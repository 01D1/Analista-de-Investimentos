"""Persistência do walk-forward técnico."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "train_months",
    "test_months",
    "setup_type",
    "windows_count",
    "positive_windows_pct",
    "mean_test_return",
    "mean_test_hit_rate",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "setup_type",
    "best_params_json",
    "train_signals",
    "test_signals",
    "train_mean_return",
    "test_mean_return",
    "train_hit_rate",
    "test_hit_rate",
    "test_positive",
    "overfitting_flag",
    "insufficient_data_flag",
    "concentration_warning",
    "stability_warning",
    "metadata_json",
]


def save_technical_walk_forward_run(db_path: str | Path, run_summary: dict, results_df: pd.DataFrame) -> int:
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO technical_walk_forward_runs (
                started_at, finished_at, status, start_date, end_date,
                train_months, test_months, setup_type, windows_count,
                positive_windows_pct, mean_test_return, mean_test_hit_rate,
                robustness_class, governance_status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_summary.get("started_at") or datetime.now().isoformat(timespec="seconds"),
                run_summary.get("finished_at") or datetime.now().isoformat(timespec="seconds"),
                run_summary.get("status"),
                run_summary.get("start_date"),
                run_summary.get("end_date"),
                int(run_summary.get("train_months") or 0),
                int(run_summary.get("test_months") or 0),
                run_summary.get("setup_type"),
                int(run_summary.get("windows_count") or 0),
                float(run_summary.get("positive_windows_pct") or 0),
                float(run_summary.get("mean_test_return") or 0),
                float(run_summary.get("mean_test_hit_rate") or 0),
                run_summary.get("robustness_class"),
                run_summary.get("governance_status"),
                json.dumps(run_summary.get("metadata", {}), ensure_ascii=False),
            ),
        )
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if not results_df.empty:
            out = results_df.copy()
            out["run_id"] = run_id
            for col in RESULT_COLUMNS:
                if col not in out.columns and col != "id":
                    out[col] = pd.NA
            out[[c for c in RESULT_COLUMNS if c != "id"]].to_sql("technical_walk_forward_results", con, if_exists="append", index=False)
        con.commit()
    return run_id


def _read(db_path: str | Path, table: str, columns: list[str], where: str = "", params: tuple | None = None, limit: int | None = None) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame(columns=columns)
    with sqlite3.connect(db_path) as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not exists:
            return pd.DataFrame(columns=columns)
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += " ORDER BY id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        df = pd.read_sql_query(sql, con, params=params or ())
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def load_technical_walk_forward_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "technical_walk_forward_runs", RUN_COLUMNS, limit=limit)


def load_technical_walk_forward_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read(db_path, "technical_walk_forward_results", RESULT_COLUMNS, where=where, params=params)

