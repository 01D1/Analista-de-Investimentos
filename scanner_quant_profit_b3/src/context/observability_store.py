"""Persistência de snapshots de SLA e observabilidade operacional."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


SOURCE_SLA_SNAPSHOT_COLUMNS = [
    "id",
    "created_at",
    "window_days",
    "source_name",
    "total_checks",
    "availability_pct",
    "ok_pct",
    "warning_pct",
    "error_pct",
    "missing_pct",
    "stale_pct",
    "avg_age_days",
    "max_age_days",
    "latest_status",
    "last_ok_at",
    "days_since_last_ok",
    "reliability_class",
    "metadata_json",
]

OBSERVABILITY_SNAPSHOT_COLUMNS = [
    "id",
    "created_at",
    "window_days",
    "overall_status",
    "overall_availability_pct",
    "total_sources",
    "critical_sources",
    "total_alerts",
    "critical_alerts",
    "open_alerts",
    "routine_success_rate_pct",
    "routine_failure_rate_pct",
    "avg_signals_covered_pct",
    "coverage_trend_direction",
    "summary_text",
    "metadata_json",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_source_sla_snapshot(db_path: str | Path, source_sla_df: pd.DataFrame, window_days: int) -> int:
    if source_sla_df is None or source_sla_df.empty:
        return 0
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    created_at = _now()
    rows = []
    for _, row in source_sla_df.iterrows():
        rows.append(
            (
                created_at,
                int(window_days),
                row.get("source_name"),
                int(row.get("total_checks") or 0),
                float(row.get("availability_pct") or 0),
                float(row.get("ok_pct") or 0),
                float(row.get("warning_pct") or 0),
                float(row.get("error_pct") or 0),
                float(row.get("missing_pct") or 0),
                float(row.get("stale_pct") or 0),
                float(row.get("avg_age_days") or 0),
                float(row.get("max_age_days") or 0),
                row.get("latest_status"),
                row.get("last_ok_at"),
                row.get("days_since_last_ok"),
                row.get("reliability_class"),
                json.dumps(row.to_dict(), ensure_ascii=False, default=str),
            )
        )
    with sqlite3.connect(db_path) as con:
        con.executemany(
            """
            INSERT INTO source_sla_snapshots (
                created_at, window_days, source_name, total_checks,
                availability_pct, ok_pct, warning_pct, error_pct,
                missing_pct, stale_pct, avg_age_days, max_age_days,
                latest_status, last_ok_at, days_since_last_ok,
                reliability_class, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
    return len(rows)


def save_operational_observability_snapshot(db_path: str | Path, summary: dict) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO operational_observability_snapshots (
                created_at, window_days, overall_status, overall_availability_pct,
                total_sources, critical_sources, total_alerts, critical_alerts,
                open_alerts, routine_success_rate_pct, routine_failure_rate_pct,
                avg_signals_covered_pct, coverage_trend_direction,
                summary_text, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                int(summary.get("window_days") or 0),
                summary.get("overall_status"),
                float(summary.get("overall_availability_pct") or 0),
                int(summary.get("total_sources") or 0),
                int(summary.get("critical_sources") or 0),
                int(summary.get("total_alerts") or 0),
                int(summary.get("critical_alerts") or 0),
                int(summary.get("open_alerts") or 0),
                float(summary.get("routine_success_rate_pct") or 0),
                float(summary.get("routine_failure_rate_pct") or 0),
                float(summary.get("avg_signals_covered_pct") or 0),
                summary.get("coverage_trend_direction"),
                summary.get("summary_text"),
                json.dumps(summary, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def _read(db_path: str | Path, table: str, columns: list[str], order: str, limit: int | None = None) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=columns)
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                return pd.DataFrame(columns=columns)
            sql = f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order}"
            if limit:
                sql += f" LIMIT {int(limit)}"
            return pd.read_sql_query(sql, con)
    except Exception:
        return pd.DataFrame(columns=columns)


def load_latest_observability_snapshot(db_path: str | Path) -> pd.DataFrame:
    return _read(
        db_path,
        "operational_observability_snapshots",
        OBSERVABILITY_SNAPSHOT_COLUMNS,
        "id DESC",
        limit=1,
    )


def load_observability_history(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    return _read(
        db_path,
        "operational_observability_snapshots",
        OBSERVABILITY_SNAPSHOT_COLUMNS,
        "id DESC",
        limit=limit,
    )
