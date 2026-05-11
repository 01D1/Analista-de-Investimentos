"""Persistência dos alertas operacionais."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.notifications.alert_engine import ALERT_COLUMNS
from src.db.init_db import init_database


OPEN_ALERT_COLUMNS = ["id", *ALERT_COLUMNS, "resolved", "resolved_at"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=OPEN_ALERT_COLUMNS)


def save_alerts(db_path: str | Path, alerts_df: pd.DataFrame) -> int:
    if alerts_df is None or alerts_df.empty:
        return 0
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    rows = []
    for _, row in alerts_df.iterrows():
        rows.append(
            (
                row.get("created_at"),
                row.get("alert_type"),
                row.get("severity"),
                row.get("title"),
                row.get("message"),
                row.get("source"),
                0,
                None,
                row.get("metadata_json"),
            )
        )
    with sqlite3.connect(db_path) as con:
        con.executemany(
            """
            INSERT INTO operational_alerts (
                created_at, alert_type, severity, title, message, source,
                resolved, resolved_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
    return len(rows)


def load_open_alerts(db_path: str | Path) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return _empty()
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operational_alerts'").fetchone()
            if not exists:
                return _empty()
            return pd.read_sql_query(
                """
                SELECT id, alert_type, severity, title, message, source,
                       created_at, metadata_json, resolved, resolved_at
                FROM operational_alerts
                WHERE COALESCE(resolved, 0) = 0
                ORDER BY id DESC
                """,
                con,
            )
    except Exception:
        return _empty()


def resolve_alert(db_path: str | Path, alert_id: int) -> bool:
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "UPDATE operational_alerts SET resolved = 1, resolved_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), int(alert_id)),
        )
        con.commit()
        return cur.rowcount > 0
