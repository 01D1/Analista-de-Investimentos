"""Persistencia de robustez das regras de paper trading."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


COMPARISON_COLUMNS = [
    "created_at",
    "simple_run_id",
    "advanced_run_id",
    "metric",
    "simple_value",
    "advanced_value",
    "delta",
    "improved",
    "material_change",
    "metadata_json",
]

OPT_RUN_COLUMNS = [
    "created_at",
    "start_date",
    "end_date",
    "objective",
    "best_params_json",
    "best_total_return",
    "best_max_drawdown",
    "best_profit_factor",
    "best_trades_count",
    "overfitting_warning",
    "metadata_json",
]

OPT_RESULT_COLUMNS = [
    "run_id",
    "params_json",
    "total_return",
    "max_drawdown",
    "sharpe",
    "sortino",
    "win_rate",
    "profit_factor",
    "trades_count",
    "turnover",
    "score_objective",
    "overfit_risk_hint",
    "metadata_json",
]

WF_RUN_COLUMNS = [
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "train_months",
    "test_months",
    "windows_count",
    "positive_windows_pct",
    "mean_test_return",
    "mean_test_drawdown",
    "mean_test_profit_factor",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

WF_RESULT_COLUMNS = [
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "best_params_json",
    "train_return",
    "test_return",
    "train_drawdown",
    "test_drawdown",
    "train_profit_factor",
    "test_profit_factor",
    "train_trades",
    "test_trades",
    "test_positive",
    "overfitting_flag",
    "turnover_warning",
    "drawdown_warning",
    "metadata_json",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _prepare(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns]


def save_paper_simulation_comparison(
    db_path: str | Path,
    simple_run_id: int | None,
    advanced_run_id: int | None,
    comparison_df: pd.DataFrame,
) -> int:
    if comparison_df is None or comparison_df.empty:
        return 0
    init_database(db_path, verbose=False)
    df = comparison_df.copy()
    df["created_at"] = _now()
    df["simple_run_id"] = simple_run_id
    df["advanced_run_id"] = advanced_run_id
    df["metadata_json"] = df.get("metadata_json", "{}")
    save = _prepare(df, COMPARISON_COLUMNS)
    with sqlite3.connect(db_path) as con:
        save.to_sql("paper_simulation_comparisons", con, if_exists="append", index=False)
    return int(len(save))


def save_paper_exit_optimization_run(
    db_path: str | Path,
    run_summary: dict,
    results_df: pd.DataFrame,
) -> int:
    init_database(db_path, verbose=False)
    best = results_df.iloc[0].to_dict() if results_df is not None and not results_df.empty else {}
    row = {
        "created_at": _now(),
        "start_date": run_summary.get("start_date"),
        "end_date": run_summary.get("end_date"),
        "objective": run_summary.get("objective", "total_return"),
        "best_params_json": best.get("params_json", "{}"),
        "best_total_return": best.get("total_return", 0),
        "best_max_drawdown": best.get("max_drawdown", 0),
        "best_profit_factor": best.get("profit_factor", 0),
        "best_trades_count": best.get("trades_count", 0),
        "overfitting_warning": "OVERFIT" in str(best.get("overfit_risk_hint", "")),
        "metadata_json": json.dumps(run_summary.get("metadata", {}), ensure_ascii=False),
    }
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([row], columns=OPT_RUN_COLUMNS).to_sql("paper_exit_optimization_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if results_df is not None and not results_df.empty:
            save = results_df.copy()
            save["run_id"] = run_id
            _prepare(save, OPT_RESULT_COLUMNS).to_sql("paper_exit_optimization_results", con, if_exists="append", index=False)
    return run_id


def save_paper_walk_forward_run(
    db_path: str | Path,
    run_summary: dict,
    results_df: pd.DataFrame,
    optimization_results_df: pd.DataFrame | None = None,
) -> int:
    init_database(db_path, verbose=False)
    now = _now()
    row = {col: run_summary.get(col) for col in WF_RUN_COLUMNS}
    row["started_at"] = row.get("started_at") or now
    row["finished_at"] = row.get("finished_at") or now
    row["status"] = row.get("status") or "COMPLETED"
    row["metadata_json"] = row.get("metadata_json") or json.dumps(run_summary.get("metadata", {}), ensure_ascii=False)
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([row], columns=WF_RUN_COLUMNS).to_sql("paper_walk_forward_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if results_df is not None and not results_df.empty:
            save = results_df.copy()
            save["run_id"] = run_id
            _prepare(save, WF_RESULT_COLUMNS).to_sql("paper_walk_forward_results", con, if_exists="append", index=False)
    if optimization_results_df is not None and not optimization_results_df.empty:
        save_paper_exit_optimization_run(db_path, run_summary, optimization_results_df)
    return run_id


def _read(db_path: str | Path, table: str, run_id: int | None = None, limit: int = 500) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con, table):
                return pd.DataFrame()
            sql = f"SELECT * FROM {table}"
            params = []
            if run_id is not None and table.endswith("_results"):
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame()


def load_paper_walk_forward_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_walk_forward_runs", limit=limit)


def load_paper_walk_forward_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_walk_forward_results", run_id=run_id, limit=5000)


def load_paper_exit_optimization_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_exit_optimization_runs", limit=limit)


def load_paper_exit_optimization_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_exit_optimization_results", run_id=run_id, limit=5000)


def load_paper_simulation_comparisons(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read(db_path, "paper_simulation_comparisons", limit=limit)
