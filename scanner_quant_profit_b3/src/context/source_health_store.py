"""Persistência dos health checks de fontes."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.context.source_health import HEALTH_COLUMNS
from src.db.init_db import init_database


SUMMARY_COLUMNS = [
    "total_sources",
    "ok_count",
    "warning_count",
    "error_count",
    "missing_count",
    "stale_count",
    "empty_count",
    "overall_status",
]


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def save_source_health_checks(db_path: str | Path, health_df: pd.DataFrame) -> int:
    if health_df is None or health_df.empty:
        return 0
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    rows = []
    for _, row in health_df.iterrows():
        rows.append(
            (
                row.get("checked_at"),
                row.get("source_name"),
                row.get("status"),
                int(bool(row.get("available"))),
                int(row.get("records_count") or 0),
                row.get("latest_date"),
                row.get("age_days"),
                row.get("coverage_hint"),
                row.get("path"),
                row.get("message"),
                row.get("metadata_json"),
            )
        )
    with sqlite3.connect(db_path) as con:
        con.executemany(
            """
            INSERT INTO source_health_checks (
                checked_at, source_name, status, available, records_count,
                latest_date, age_days, coverage_hint, path, message, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
    return len(rows)


def load_latest_source_health_checks(db_path: str | Path) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return _empty(["id"] + HEALTH_COLUMNS)
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_health_checks'").fetchone()
            if not exists:
                return _empty(["id"] + HEALTH_COLUMNS)
            latest = con.execute("SELECT MAX(checked_at) FROM source_health_checks").fetchone()[0]
            if latest is None:
                return _empty(["id"] + HEALTH_COLUMNS)
            return pd.read_sql_query(
                "SELECT id, checked_at, source_name, status, available, records_count, latest_date, age_days, coverage_hint, path, message, metadata_json FROM source_health_checks WHERE checked_at = ? ORDER BY source_name",
                con,
                params=(latest,),
            )
    except Exception:
        return _empty(["id"] + HEALTH_COLUMNS)


def load_source_health_history(db_path: str | Path, source_name: str | None = None, limit: int = 500) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return _empty(["id"] + HEALTH_COLUMNS)
    where = "WHERE source_name = ?" if source_name else ""
    params = (source_name,) if source_name else ()
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_health_checks'").fetchone()
            if not exists:
                return _empty(["id"] + HEALTH_COLUMNS)
            return pd.read_sql_query(
                f"SELECT id, checked_at, source_name, status, available, records_count, latest_date, age_days, coverage_hint, path, message, metadata_json FROM source_health_checks {where} ORDER BY checked_at DESC LIMIT ?",
                con,
                params=(*params, int(limit)),
            )
    except Exception:
        return _empty(["id"] + HEALTH_COLUMNS)


def summarize_source_health(health_df: pd.DataFrame) -> dict:
    if health_df is None or health_df.empty:
        return {
            "total_sources": 0,
            "ok_count": 0,
            "warning_count": 0,
            "error_count": 0,
            "missing_count": 0,
            "stale_count": 0,
            "empty_count": 0,
            "overall_status": "UNKNOWN",
        }
    status = health_df.get("status", pd.Series(dtype=str)).fillna("UNKNOWN").astype(str).str.upper()
    counts = status.value_counts().to_dict()
    if any(counts.get(s, 0) for s in ["ERROR", "MISSING"]):
        overall = "ERROR"
    elif any(counts.get(s, 0) for s in ["WARNING", "STALE", "EMPTY", "UNKNOWN"]):
        overall = "WARNING"
    else:
        overall = "OK"
    return {
        "total_sources": int(len(health_df)),
        "ok_count": int(counts.get("OK", 0)),
        "warning_count": int(counts.get("WARNING", 0)),
        "error_count": int(counts.get("ERROR", 0)),
        "missing_count": int(counts.get("MISSING", 0)),
        "stale_count": int(counts.get("STALE", 0)),
        "empty_count": int(counts.get("EMPTY", 0)),
        "overall_status": overall,
    }
