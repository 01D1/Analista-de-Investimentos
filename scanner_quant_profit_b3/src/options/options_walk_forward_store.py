"""Persistência do walk-forward de estruturas de opções."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database


WF_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "structure_type",
    "train_months",
    "test_months",
    "windows_count",
    "positive_windows_pct",
    "mean_test_net_return",
    "mean_test_win_rate",
    "mean_test_profit_factor",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

WF_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "train_trades",
    "test_trades",
    "train_mean_net_return",
    "test_mean_net_return",
    "train_win_rate",
    "test_win_rate",
    "train_profit_factor",
    "test_profit_factor",
    "avg_cost_drag",
    "skipped_pct",
    "positive_test_window",
    "overfitting_flag",
    "insufficient_data_flag",
    "metadata_json",
]

CONTEXT_COLUMNS = [
    "id",
    "run_id",
    "context_type",
    "context_value",
    "trades",
    "mean_net_return",
    "win_rate",
    "profit_factor",
    "avg_cost_drag",
    "skipped_pct",
    "metadata_json",
]


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def save_options_walk_forward_run(db_path: str | Path, run_summary: dict[str, Any], results_df: pd.DataFrame, context_summary_df: pd.DataFrame | None = None) -> int:
    path = Path(db_path)
    init_database(path, verbose=False)
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(path) as con:
        cur = con.execute(
            """
            INSERT INTO option_walk_forward_runs (
                started_at, finished_at, status, start_date, end_date, structure_type,
                train_months, test_months, windows_count, positive_windows_pct,
                mean_test_net_return, mean_test_win_rate, mean_test_profit_factor,
                robustness_class, governance_status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_summary.get("started_at") or now,
                run_summary.get("finished_at") or now,
                run_summary.get("status", "SUCCESS"),
                run_summary.get("start_date"),
                run_summary.get("end_date"),
                run_summary.get("structure_type"),
                int(run_summary.get("train_months") or 0),
                int(run_summary.get("test_months") or 0),
                int(run_summary.get("windows_count") or 0),
                float(run_summary.get("positive_windows_pct") or 0),
                float(run_summary.get("mean_test_net_return") or 0),
                float(run_summary.get("mean_test_win_rate") or 0),
                float(run_summary.get("mean_test_profit_factor") or 0),
                run_summary.get("robustness_class"),
                run_summary.get("governance_status"),
                json.dumps(run_summary.get("metadata", {}), ensure_ascii=False),
            ),
        )
        run_id = int(cur.lastrowid)
        if results_df is not None and not results_df.empty:
            save = results_df.copy()
            save["run_id"] = run_id
            for col in WF_RESULT_COLUMNS:
                if col not in save.columns and col != "id":
                    save[col] = pd.NA
            save[[c for c in WF_RESULT_COLUMNS if c != "id"]].to_sql("option_walk_forward_results", con, if_exists="append", index=False)
        if context_summary_df is not None and not context_summary_df.empty:
            ctx = context_summary_df.copy()
            ctx["run_id"] = run_id
            for col in CONTEXT_COLUMNS:
                if col not in ctx.columns and col != "id":
                    ctx[col] = pd.NA
            ctx[[c for c in CONTEXT_COLUMNS if c != "id"]].to_sql("option_context_summary", con, if_exists="append", index=False)
        con.commit()
    return run_id


def load_options_walk_forward_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "option_walk_forward_runs", WF_RUN_COLUMNS, f"ORDER BY id DESC LIMIT {int(limit)}")


def load_options_walk_forward_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = f"WHERE run_id = {int(run_id)}" if run_id is not None else ""
    return _read(db_path, "option_walk_forward_results", WF_RESULT_COLUMNS, f"{where} ORDER BY id DESC")


def load_options_context_summary(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = f"WHERE run_id = {int(run_id)}" if run_id is not None else ""
    return _read(db_path, "option_context_summary", CONTEXT_COLUMNS, f"{where} ORDER BY id DESC")


def _read(db_path: str | Path, table: str, columns: list[str], suffix: str = "") -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return _empty(columns)
    try:
        with sqlite3.connect(path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                return _empty(columns)
            df = pd.read_sql_query(f"SELECT * FROM {table} {suffix}", con)
    except sqlite3.Error:
        return _empty(columns)
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]

