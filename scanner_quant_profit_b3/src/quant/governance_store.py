"""Persistência de reviews de governança quantitativa."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database


GOVERNANCE_REVIEW_COLUMNS = [
    "id",
    "created_at",
    "source_type",
    "source_run_id",
    "candidate_name",
    "governance_status",
    "approved",
    "risk_level",
    "confidence_level",
    "total_signals",
    "windows_count",
    "positive_windows_pct",
    "mean_net_return",
    "mean_hit_rate",
    "avg_top_3_concentration_pct",
    "overfitting_alert",
    "sample_warning",
    "concentration_warning",
    "liquidity_warning",
    "regime_status",
    "allowed_regimes_json",
    "blocked_regimes_json",
    "event_status",
    "allowed_event_contexts_json",
    "blocked_event_contexts_json",
    "summary_text",
    "reasons_for_json",
    "reasons_against_json",
    "required_actions_json",
    "metadata_json",
]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=GOVERNANCE_REVIEW_COLUMNS)


def _table_exists(con: sqlite3.Connection) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='governance_reviews'"
    ).fetchone() is not None


def _metrics(review: dict[str, Any]) -> dict[str, Any]:
    return review.get("metrics") or review.get("metadata", {}).get("metrics") or review


def save_governance_review(db_path: str | Path, review: dict[str, Any]) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    metrics = _metrics(review)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO governance_reviews (
                created_at, source_type, source_run_id, candidate_name,
                governance_status, approved, risk_level, confidence_level,
                total_signals, windows_count, positive_windows_pct, mean_net_return,
                mean_hit_rate, avg_top_3_concentration_pct,
                overfitting_alert, sample_warning, concentration_warning, liquidity_warning,
                regime_status, allowed_regimes_json, blocked_regimes_json,
                event_status, allowed_event_contexts_json, blocked_event_contexts_json,
                summary_text, reasons_for_json, reasons_against_json,
                required_actions_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                review.get("source_type"),
                review.get("source_run_id"),
                review.get("candidate_name"),
                review.get("governance_status"),
                int(bool(review.get("approved"))),
                review.get("risk_level"),
                review.get("confidence_level"),
                metrics.get("total_signals"),
                metrics.get("windows_count"),
                metrics.get("positive_windows_pct"),
                metrics.get("mean_test_net_return", metrics.get("mean_net_return")),
                metrics.get("mean_hit_rate", metrics.get("mean_test_hit_rate")),
                metrics.get("avg_top_3_concentration_pct"),
                int(bool(metrics.get("overfitting_alert"))),
                int(bool(metrics.get("sample_warning"))),
                int(bool(metrics.get("concentration_warning"))),
                int(bool(metrics.get("liquidity_warning"))),
                review.get("regime_status"),
                json.dumps(review.get("allowed_regimes", []), ensure_ascii=False, default=str),
                json.dumps(review.get("blocked_regimes", []), ensure_ascii=False, default=str),
                review.get("event_status"),
                json.dumps(review.get("allowed_event_contexts", []), ensure_ascii=False, default=str),
                json.dumps(review.get("blocked_event_contexts", []), ensure_ascii=False, default=str),
                review.get("summary_text"),
                json.dumps(review.get("reasons_for", []), ensure_ascii=False, default=str),
                json.dumps(review.get("reasons_against", []), ensure_ascii=False, default=str),
                json.dumps(review.get("required_actions", []), ensure_ascii=False, default=str),
                json.dumps(review, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def load_governance_reviews(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return _empty()
    try:
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con):
                return _empty()
            df = pd.read_sql_query(
                f"SELECT {', '.join(GOVERNANCE_REVIEW_COLUMNS)} FROM governance_reviews ORDER BY id DESC LIMIT ?",
                con,
                params=(int(limit),),
            )
    except Exception:
        return _empty()
    for col in GOVERNANCE_REVIEW_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[GOVERNANCE_REVIEW_COLUMNS]


def load_latest_governance_review(db_path: str | Path, source_type: str | None = None) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return _empty()
    try:
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con):
                return _empty()
            where = "WHERE source_type = ?" if source_type else ""
            params = (source_type,) if source_type else ()
            df = pd.read_sql_query(
                f"SELECT {', '.join(GOVERNANCE_REVIEW_COLUMNS)} FROM governance_reviews {where} ORDER BY id DESC LIMIT 1",
                con,
                params=params,
            )
    except Exception:
        return _empty()
    for col in GOVERNANCE_REVIEW_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[GOVERNANCE_REVIEW_COLUMNS]


def summarize_governance_reviews(db_path: str | Path) -> pd.DataFrame:
    df = load_governance_reviews(db_path, limit=1000)
    columns = ["governance_status", "reviews", "approved_count", "latest_created_at"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for status, group in df.groupby("governance_status", dropna=False):
        rows.append(
            {
                "governance_status": status,
                "reviews": int(len(group)),
                "approved_count": int(pd.to_numeric(group.get("approved"), errors="coerce").fillna(0).sum()),
                "latest_created_at": group["created_at"].max(),
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("reviews", ascending=False).reset_index(drop=True)
