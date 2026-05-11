from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.context.event_model import EVENT_COLUMNS


DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "12_PYTHON" / "pipeline banco completo" / "data" / "qualitative"


def _date_from_source(source: str | None):
    if not source:
        return None
    match = pd.Series([source]).str.extract(r"(\d{4}-\d{2}-\d{2})").iloc[0, 0]
    return match if isinstance(match, str) else None


def load_events(start_date=None, end_date=None, tickers=None, root_path: str | Path | None = None) -> pd.DataFrame:
    root = Path(root_path) if root_path else DEFAULT_ROOT
    events_root = root / "events"
    if not events_root.exists():
        return pd.DataFrame(columns=EVENT_COLUMNS)
    paths = []
    if tickers:
        for ticker in tickers:
            paths.extend((events_root / ticker.upper()).glob("events.json"))
    else:
        paths = list(events_root.glob("*/events.json"))
    rows = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            event_date = item.get("date") or _date_from_source(item.get("source_document"))
            if not event_date:
                continue
            event_date = pd.to_datetime(event_date, errors="coerce")
            if pd.isna(event_date):
                continue
            event_date_str = event_date.strftime("%Y-%m-%d")
            if start_date and event_date_str < start_date:
                continue
            if end_date and event_date_str > end_date:
                continue
            rows.append(
                {
                    "event_date": event_date_str,
                    "ticker": item.get("ticker") or path.parent.name.upper(),
                    "event_type": item.get("event_type") or "",
                    "event_source": "releases",
                    "event_title": item.get("title") or item.get("source_document") or "",
                    "event_summary": item.get("description") or item.get("evidence") or "",
                    "impact_direction": "POSITIVO" if item.get("thesis_effect") == "melhora" else "NEGATIVO" if item.get("thesis_effect") == "piora" else "INCERTO",
                    "impact_score": 0.8 if item.get("relevance") == "alta" else 0.5 if item.get("relevance") == "media" else 0.25,
                    "confidence": 0.75,
                    "metadata_json": {"source_file": str(path), "source_document": item.get("source_document"), "relevance": item.get("relevance")},
                }
            )
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)

