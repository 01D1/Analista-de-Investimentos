"""Persistencia das reconciliacoes de fontes."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RECONCILIATION_RESULT_COLUMNS = [
    "id",
    "run_id",
    "source_domain",
    "issue_type",
    "severity",
    "status",
    "description",
    "suggested_command",
    "executed",
    "execution_status",
    "metadata_json",
]


def save_reconciliation_run(db_path: str | Path, summary: dict, results_df: pd.DataFrame) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO data_reconciliation_runs (
                started_at, finished_at, reconciliation_type, status, issues_count,
                fixes_suggested_count, fixes_executed_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.get("started_at", datetime.now().isoformat(timespec="seconds")),
                summary.get("finished_at", datetime.now().isoformat(timespec="seconds")),
                summary.get("reconciliation_type", "all"),
                summary.get("status", "UNKNOWN"),
                int(summary.get("issues_count", 0) or 0),
                int(summary.get("fixes_suggested_count", 0) or 0),
                int(summary.get("fixes_executed_count", 0) or 0),
                json.dumps(summary.get("metadata", {}), ensure_ascii=False, default=str),
            ),
        )
        run_id = int(cur.lastrowid)
        if results_df is not None and not results_df.empty:
            rows = []
            for _, row in results_df.iterrows():
                rows.append(
                    (
                        run_id,
                        row.get("source_domain"),
                        row.get("issue_type"),
                        row.get("severity"),
                        row.get("status"),
                        row.get("description"),
                        row.get("suggested_command"),
                        1 if bool(row.get("executed")) else 0,
                        row.get("execution_status"),
                        row.get("metadata_json"),
                    )
                )
            con.executemany(
                """
                INSERT INTO data_reconciliation_results (
                    run_id, source_domain, issue_type, severity, status, description,
                    suggested_command, executed, execution_status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        con.commit()
    return run_id


def load_latest_reconciliation_results(db_path: str | Path, reconciliation_type: str | None = None) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=RECONCILIATION_RESULT_COLUMNS)
    try:
        with sqlite3.connect(db_path) as con:
            params: list = []
            where = ""
            if reconciliation_type:
                where = "WHERE reconciliation_type = ?"
                params.append(reconciliation_type)
            run = con.execute(f"SELECT id FROM data_reconciliation_runs {where} ORDER BY id DESC LIMIT 1", params).fetchone()
            if not run:
                return pd.DataFrame(columns=RECONCILIATION_RESULT_COLUMNS)
            return pd.read_sql_query("SELECT * FROM data_reconciliation_results WHERE run_id = ? ORDER BY id", con, params=(int(run[0]),))
    except Exception:
        return pd.DataFrame(columns=RECONCILIATION_RESULT_COLUMNS)


def load_reconciliation_history(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            return pd.read_sql_query("SELECT * FROM data_reconciliation_runs ORDER BY id DESC LIMIT ?", con, params=(int(limit),))
    except Exception:
        return pd.DataFrame()

