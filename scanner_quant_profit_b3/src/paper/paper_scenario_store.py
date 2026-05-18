"""Persistencia da validacao multi-cenario do paper trading."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = [
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "periods_count",
    "scenarios_count",
    "signal_sources_count",
    "positive_periods_pct",
    "mean_return",
    "mean_drawdown",
    "governance_status",
    "metadata_json",
]

RESULT_COLUMNS = [
    "run_id",
    "period_id",
    "scenario_id",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "total_return",
    "max_drawdown",
    "sharpe",
    "sortino",
    "win_rate",
    "profit_factor",
    "trades_count",
    "turnover",
    "cost_bps",
    "slippage_bps",
    "governance_status",
    "metadata_json",
]

COST_COLUMNS = [
    "run_id",
    "cost_scenario",
    "cost_bps",
    "slippage_bps",
    "mean_return",
    "mean_drawdown",
    "positive_periods_pct",
    "cost_robustness_class",
    "metadata_json",
]

SOURCE_COLUMNS = [
    "run_id",
    "signal_source",
    "mean_return",
    "mean_drawdown",
    "win_rate",
    "profit_factor",
    "trades_count",
    "robustness_class",
    "metadata_json",
]


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _prepare(df: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    out = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns]


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def save_paper_scenario_validation_run(
    db_path: str | Path,
    run_summary: dict,
    results_df: pd.DataFrame,
    cost_df: pd.DataFrame | None = None,
    signal_source_df: pd.DataFrame | None = None,
) -> int:
    init_database(db_path, verbose=False)
    now = _now()
    row = {col: run_summary.get(col) for col in RUN_COLUMNS}
    row["started_at"] = row.get("started_at") or now
    row["finished_at"] = row.get("finished_at") or now
    row["status"] = row.get("status") or "COMPLETED"
    row["metadata_json"] = row.get("metadata_json") or json.dumps(run_summary.get("metadata", {}), ensure_ascii=False)
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([row], columns=RUN_COLUMNS).to_sql("paper_scenario_validation_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if results_df is not None and not results_df.empty:
            results = results_df.copy()
            results["run_id"] = run_id
            _prepare(results, RESULT_COLUMNS).to_sql("paper_scenario_validation_results", con, if_exists="append", index=False)
        if cost_df is not None and not cost_df.empty:
            costs = cost_df.copy()
            costs["run_id"] = run_id
            _prepare(costs, COST_COLUMNS).to_sql("paper_cost_sensitivity_results", con, if_exists="append", index=False)
        if signal_source_df is not None and not signal_source_df.empty:
            sources = signal_source_df.copy()
            sources["run_id"] = run_id
            _prepare(sources, SOURCE_COLUMNS).to_sql("paper_signal_source_comparison", con, if_exists="append", index=False)
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
            if run_id is not None and table != "paper_scenario_validation_runs":
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame()


def load_paper_scenario_validation_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_scenario_validation_runs", limit=limit)


def load_paper_scenario_validation_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_scenario_validation_results", run_id=run_id, limit=5000)


def load_paper_cost_sensitivity_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_cost_sensitivity_results", run_id=run_id, limit=5000)


def load_paper_signal_source_comparison(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_signal_source_comparison", run_id=run_id, limit=5000)
