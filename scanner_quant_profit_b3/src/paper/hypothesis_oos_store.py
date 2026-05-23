"""Persistencia da validacao OOS de hipoteses de investigacao."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = [
    "created_at",
    "hypothesis_id",
    "hypothesis_type",
    "target",
    "windows_count",
    "scenarios_count",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

RESULT_COLUMNS = [
    "run_id",
    "window_id",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "base_return",
    "hypothesis_return",
    "return_delta",
    "base_drawdown",
    "hypothesis_drawdown",
    "drawdown_delta",
    "base_fragility_score",
    "hypothesis_fragility_score",
    "fragility_delta",
    "trades_count",
    "improvement_detected",
    "overfitting_flag",
    "cost_sensitivity_flag",
    "regime_instability_flag",
    "metadata_json",
]

COVERAGE_COLUMNS = [
    "run_id",
    "window_id",
    "scenario_name",
    "signal_source",
    "regime_filter",
    "start_date",
    "end_date",
    "signals_count",
    "price_days_count",
    "tickers_count",
    "useful_cell",
    "source_coverage_status",
    "message",
    "metadata_json",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prepare(df: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    out = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns]


def save_hypothesis_oos_run(db_path: str | Path, summary: dict, results_df: pd.DataFrame, coverage_df: pd.DataFrame | None = None) -> int:
    init_database(db_path, verbose=False)
    row = {col: summary.get(col) for col in RUN_COLUMNS}
    row["created_at"] = row.get("created_at") or _now()
    row["metadata_json"] = row.get("metadata_json") or json.dumps(summary.get("metadata", {}), ensure_ascii=False)
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([row], columns=RUN_COLUMNS).to_sql("paper_hypothesis_oos_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if results_df is not None and not results_df.empty:
            save = results_df.copy()
            save["run_id"] = run_id
            _prepare(save, RESULT_COLUMNS).to_sql("paper_hypothesis_oos_results", con, if_exists="append", index=False)
        if coverage_df is not None and not coverage_df.empty:
            coverage = coverage_df.copy()
            coverage["run_id"] = run_id
            _prepare(coverage, COVERAGE_COLUMNS).to_sql("paper_hypothesis_oos_coverage", con, if_exists="append", index=False)
    return run_id


def _read(db_path: str | Path, table: str, run_id: int | None = None, limit: int = 500) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return pd.DataFrame()
            sql = f"SELECT * FROM {table}"
            params: list = []
            if run_id is not None and table != "paper_hypothesis_oos_runs":
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame()


def load_hypothesis_oos_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_oos_runs", limit=limit)


def load_hypothesis_oos_results(db_path: str | Path, run_id: int | None = None, limit: int = 5000) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_oos_results", run_id=run_id, limit=limit)


def load_hypothesis_oos_coverage(db_path: str | Path, run_id: int | None = None, limit: int = 5000) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_oos_coverage", run_id=run_id, limit=limit)
