"""Normalização, deduplicação e merge de eventos."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import pandas as pd

from src.context.event_classifier import classify_event_type, estimate_event_impact
from src.context.event_model import EVENT_COLUMNS, normalize_event_record as _base_normalize


SOURCE_PRIORITY = {
    "cvm": 100,
    "releases": 80,
    "news_hunter": 60,
    "manual": 50,
    "csv": 40,
}


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""


def normalize_event_record(row: dict[str, Any] | pd.Series) -> dict[str, Any]:
    data = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    title = data.get("event_title") or data.get("title") or data.get("titulo") or data.get("Assunto") or ""
    summary = data.get("event_summary") or data.get("summary") or data.get("conteudo") or data.get("description") or data.get("evidence") or ""
    if not data.get("event_title"):
        data["event_title"] = title
    if not data.get("event_summary"):
        data["event_summary"] = summary
    if _missing(data.get("event_type")):
        data["event_type"] = classify_event_type(title, summary, data.get("event_source"))
    impact = estimate_event_impact(title, summary, data.get("event_type"))
    if _missing(data.get("impact_direction")):
        data["impact_direction"] = impact["impact_direction"]
    if _missing(data.get("impact_score")):
        data["impact_score"] = impact["impact_score"]
    if _missing(data.get("confidence")):
        data["confidence"] = impact["confidence"]
    normalized = _base_normalize(data)
    normalized["coverage_source"] = data.get("coverage_source") or normalized.get("event_source")
    return normalized


def normalize_events(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df is None or events_df.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS + ["coverage_source"])
    return pd.DataFrame([normalize_event_record(row) for _, row in events_df.iterrows()])


def _title_key(title: Any) -> str:
    text = str(title or "").lower()
    text = re.sub(r"[^a-z0-9áàâãéêíóôõúç ]+", " ", text)
    tokens = [token for token in text.split() if len(token) > 2]
    return " ".join(tokens[:8])


def _group_key(row: pd.Series) -> str:
    raw = f"{row.get('ticker','')}|{row.get('event_date','')}|{row.get('event_type','')}|{_title_key(row.get('event_title'))}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def deduplicate_events(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df is None or events_df.empty:
        return pd.DataFrame(columns=list(events_df.columns) if events_df is not None else EVENT_COLUMNS)
    df = normalize_events(events_df)
    df["duplicate_group_id"] = df.apply(_group_key, axis=1)
    df["_confidence"] = pd.to_numeric(df.get("confidence"), errors="coerce").fillna(0)
    df["_source_priority"] = df.get("event_source", "").astype(str).str.lower().map(SOURCE_PRIORITY).fillna(0)
    df = df.sort_values(["duplicate_group_id", "_confidence", "_source_priority"], ascending=[True, False, False]).reset_index(drop=True)
    df["canonical_event_id"] = df.groupby("duplicate_group_id").cumcount()
    df["is_duplicate"] = df["canonical_event_id"] > 0
    canonical_by_group = df.groupby("duplicate_group_id").head(1).set_index("duplicate_group_id").index.to_series().to_dict()
    df["canonical_event_id"] = df["duplicate_group_id"].map(canonical_by_group)
    return df.drop(columns=["_confidence", "_source_priority"])


def merge_duplicate_events(events_df: pd.DataFrame) -> pd.DataFrame:
    marked = deduplicate_events(events_df)
    if marked.empty:
        return marked
    rows = []
    for _, group in marked.groupby("duplicate_group_id", dropna=False):
        work = group.copy()
        work["_confidence"] = pd.to_numeric(work.get("confidence"), errors="coerce").fillna(0)
        work["_source_priority"] = work.get("event_source", "").astype(str).str.lower().map(SOURCE_PRIORITY).fillna(0)
        canonical = work.sort_values(["_confidence", "_source_priority"], ascending=[False, False]).iloc[0].to_dict()
        urls = [url for url in work.get("event_url", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if url]
        sources = [src for src in work.get("event_source", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if src]
        metadata = {}
        try:
            metadata = json.loads(canonical.get("metadata_json") or "{}")
        except (TypeError, ValueError):
            metadata = {}
        metadata.update({"duplicate_urls": urls, "duplicate_sources": sources, "duplicates_count": int(len(work))})
        canonical["metadata_json"] = json.dumps(metadata, ensure_ascii=False, default=str)
        canonical["is_duplicate"] = False
        rows.append(canonical)
    out = pd.DataFrame(rows)
    for col in ["_confidence", "_source_priority"]:
        if col in out.columns:
            out = out.drop(columns=[col])
    return out.reset_index(drop=True)
