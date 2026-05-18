"""Persistência de backtests preliminares de estruturas de opções."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "underlyings",
    "structure_type",
    "entries_count",
    "completed_count",
    "skipped_count",
    "mean_net_return",
    "win_rate",
    "profit_factor",
    "avg_cost_drag",
    "metadata_json",
]

RESULT_COLUMNS = [
    "id",
    "run_id",
    "entry_date",
    "exit_date",
    "underlying",
    "structure_type",
    "maturity_date",
    "dte_entry",
    "dte_exit",
    "legs_json",
    "entry_debit",
    "entry_credit",
    "exit_value",
    "gross_pnl",
    "net_pnl",
    "gross_return",
    "net_return",
    "max_loss",
    "return_on_risk",
    "exit_reason",
    "liquidity_score",
    "spread_cost",
    "transaction_cost",
    "slippage_cost",
    "execution_quality",
    "status",
    "metadata_json",
]


def _empty(cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=cols)


def save_option_structure_backtest_run(db_path: str | Path, run_summary: dict[str, Any], results_df: pd.DataFrame | None) -> int:
    path = Path(db_path)
    init_database(path, verbose=False)
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(path) as con:
        cur = con.execute(
            """
            INSERT INTO option_structure_backtest_runs (
                started_at, finished_at, status, start_date, end_date, underlyings,
                structure_type, entries_count, completed_count, skipped_count,
                mean_net_return, win_rate, profit_factor, avg_cost_drag, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_summary.get("started_at") or now,
                run_summary.get("finished_at") or now,
                run_summary.get("status", "SUCCESS"),
                run_summary.get("start_date"),
                run_summary.get("end_date"),
                run_summary.get("underlyings"),
                run_summary.get("structure_type"),
                int(run_summary.get("entries_count") or run_summary.get("total_trades") or 0),
                int(run_summary.get("completed_count") or 0),
                int(run_summary.get("skipped_count") or 0),
                float(run_summary.get("mean_net_return") or 0),
                float(run_summary.get("win_rate") or 0),
                float(run_summary.get("profit_factor") or 0),
                float(run_summary.get("avg_cost_drag") or 0),
                json.dumps(run_summary.get("metadata", {}), ensure_ascii=False),
            ),
        )
        run_id = int(cur.lastrowid)
        if results_df is not None and not results_df.empty:
            save = results_df.copy()
            save["run_id"] = run_id
            for col in RESULT_COLUMNS:
                if col not in save.columns and col != "id":
                    save[col] = pd.NA
            save[[c for c in RESULT_COLUMNS if c != "id"]].to_sql("option_structure_backtest_results", con, if_exists="append", index=False)
        con.commit()
    return run_id


def load_option_structure_backtest_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return _empty(RUN_COLUMNS)
    try:
        with sqlite3.connect(path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='option_structure_backtest_runs'").fetchone()
            if not exists:
                return _empty(RUN_COLUMNS)
            return pd.read_sql_query("SELECT * FROM option_structure_backtest_runs ORDER BY id DESC LIMIT ?", con, params=(limit,))
    except sqlite3.Error:
        return _empty(RUN_COLUMNS)


def load_option_structure_backtest_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return _empty(RESULT_COLUMNS)
    sql = "SELECT * FROM option_structure_backtest_results"
    params: tuple[Any, ...] = ()
    if run_id is not None:
        sql += " WHERE run_id = ?"
        params = (int(run_id),)
    sql += " ORDER BY id DESC"
    try:
        with sqlite3.connect(path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='option_structure_backtest_results'").fetchone()
            if not exists:
                return _empty(RESULT_COLUMNS)
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return _empty(RESULT_COLUMNS)

