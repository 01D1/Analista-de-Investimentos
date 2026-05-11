"""Persistência dos runs de retenção operacional."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database


RETENTION_CLEANUP_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "dry_run",
    "status",
    "tables_evaluated",
    "rows_candidates",
    "rows_archived",
    "rows_deleted",
    "archive_dir",
    "warnings_count",
    "errors_count",
    "metadata_json",
]

RETENTION_CLEANUP_DETAIL_COLUMNS = [
    "id",
    "run_id",
    "table_name",
    "cutoff_date",
    "rows_total",
    "rows_to_delete",
    "rows_archived",
    "rows_deleted",
    "protected",
    "status",
    "archive_path",
    "message",
    "metadata_json",
]


def save_retention_cleanup_run(db_path: str | Path, summary: dict[str, Any], details: pd.DataFrame) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO retention_cleanup_runs (
                started_at, finished_at, dry_run, status, tables_evaluated,
                rows_candidates, rows_archived, rows_deleted, archive_dir,
                warnings_count, errors_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.get("started_at"),
                summary.get("finished_at"),
                int(summary.get("dry_run") or 0),
                summary.get("status"),
                int(summary.get("tables_evaluated") or 0),
                int(summary.get("rows_candidates") or 0),
                int(summary.get("rows_archived") or 0),
                int(summary.get("rows_deleted") or 0),
                summary.get("archive_dir"),
                int(summary.get("warnings_count") or 0),
                int(summary.get("errors_count") or 0),
                json.dumps(summary, ensure_ascii=False, default=str),
            ),
        )
        run_id = int(cur.lastrowid)
        rows = []
        if details is not None and not details.empty:
            for _, row in details.iterrows():
                rows.append(
                    (
                        run_id,
                        row.get("table_name"),
                        row.get("cutoff_date"),
                        int(row.get("rows_total") or 0),
                        int(row.get("rows_to_delete") or 0),
                        int(row.get("rows_archived") or 0),
                        int(row.get("rows_deleted") or 0),
                        int(row.get("protected") or 0),
                        row.get("status"),
                        row.get("archive_path"),
                        row.get("message"),
                        json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                    )
                )
        if rows:
            con.executemany(
                """
                INSERT INTO retention_cleanup_details (
                    run_id, table_name, cutoff_date, rows_total, rows_to_delete,
                    rows_archived, rows_deleted, protected, status, archive_path,
                    message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        con.commit()
        return run_id


def _read(db_path: str | Path, table: str, columns: list[str], order: str, limit: int | None = None, where: str = "", params: tuple | None = None) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=columns)
    try:
        with sqlite3.connect(db_path) as con:
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                return pd.DataFrame(columns=columns)
            sql = f"SELECT {', '.join(columns)} FROM {table}"
            if where:
                sql += f" WHERE {where}"
            sql += f" ORDER BY {order}"
            if limit:
                sql += f" LIMIT {int(limit)}"
            return pd.read_sql_query(sql, con, params=params or ())
    except Exception:
        return pd.DataFrame(columns=columns)


def load_retention_cleanup_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "retention_cleanup_runs", RETENTION_CLEANUP_RUN_COLUMNS, "id DESC", limit=limit)


def load_retention_cleanup_details(db_path: str | Path, run_id: int) -> pd.DataFrame:
    return _read(
        db_path,
        "retention_cleanup_details",
        RETENTION_CLEANUP_DETAIL_COLUMNS,
        "id",
        where="run_id = ?",
        params=(int(run_id),),
    )
