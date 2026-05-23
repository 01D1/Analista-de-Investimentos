"""Persistência dos diagnósticos de custo/slippage."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = [
    "id",
    "created_at",
    "paper_run_id",
    "total_transaction_cost",
    "total_slippage_cost",
    "total_cost_drag",
    "cost_drag_pct_of_gross_pnl",
    "slippage_pct_of_gross_pnl",
    "avg_cost_per_trade",
    "avg_slippage_per_trade",
    "cost_drag_class",
    "metadata_json",
]

BY_TICKER_COLUMNS = [
    "id",
    "run_id",
    "ticker",
    "trades_count",
    "gross_pnl",
    "transaction_cost",
    "slippage_cost",
    "total_cost_drag",
    "cost_drag_pct",
    "cost_drag_class",
    "metadata_json",
]

BY_SOURCE_COLUMNS = [
    "id",
    "run_id",
    "signal_source",
    "trades_count",
    "gross_pnl",
    "transaction_cost",
    "slippage_cost",
    "total_cost_drag",
    "cost_drag_pct",
    "cost_drag_class",
    "metadata_json",
]

TURNOVER_COLUMNS = [
    "id",
    "run_id",
    "trades_per_day",
    "average_holding_period",
    "turnover_total",
    "turnover_daily_avg",
    "turnover_to_return_ratio",
    "overtrading_flag",
    "stop_take_turnover_flag",
    "source_turnover_flag",
    "asset_turnover_flag",
    "metadata_json",
]

BREAKEVEN_COLUMNS = [
    "id",
    "run_id",
    "max_cost_bps_supported",
    "max_slippage_bps_supported",
    "breakeven_turnover_reduction",
    "breakeven_trade_return_required",
    "negative_return_scenario",
    "metadata_json",
]


def _prepare(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns and col != "id":
            out[col] = pd.NA
    return out[[c for c in columns if c != "id"]]


def save_cost_diagnostics_run(
    db_path: str | Path,
    paper_run_id: int,
    cost_summary: dict,
    cost_by_ticker: pd.DataFrame | None = None,
    cost_by_signal_source: pd.DataFrame | None = None,
    turnover_summary: dict | None = None,
    breakeven_summary: dict | None = None,
    metadata: dict | None = None,
) -> int:
    init_database(db_path, verbose=False)
    run_row = {col: cost_summary.get(col) for col in RUN_COLUMNS if col not in {"id", "created_at", "paper_run_id", "metadata_json"}}
    run_row["created_at"] = datetime.utcnow().isoformat(timespec="seconds")
    run_row["paper_run_id"] = int(paper_run_id)
    run_row["metadata_json"] = json.dumps(metadata or {}, ensure_ascii=False, default=str)
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([run_row]).to_sql("paper_cost_diagnostics_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if cost_by_ticker is not None and not cost_by_ticker.empty:
            ticker_df = cost_by_ticker.rename(columns={"holding_period": "ticker"}).copy()
            ticker_df["run_id"] = run_id
            _prepare(ticker_df, BY_TICKER_COLUMNS).to_sql("paper_cost_diagnostics_by_ticker", con, if_exists="append", index=False)
        if cost_by_signal_source is not None and not cost_by_signal_source.empty:
            source_df = cost_by_signal_source.copy()
            source_df["run_id"] = run_id
            _prepare(source_df, BY_SOURCE_COLUMNS).to_sql("paper_cost_diagnostics_by_signal_source", con, if_exists="append", index=False)
        if turnover_summary is not None:
            turn = dict(turnover_summary)
            turn["run_id"] = run_id
            pd.DataFrame([turn]).pipe(_prepare, TURNOVER_COLUMNS).to_sql("paper_turnover_diagnostics", con, if_exists="append", index=False)
        if breakeven_summary is not None:
            be = dict(breakeven_summary)
            be["run_id"] = run_id
            pd.DataFrame([be]).pipe(_prepare, BREAKEVEN_COLUMNS).to_sql("paper_cost_breakeven", con, if_exists="append", index=False)
    return run_id


def _read(db_path: str | Path, table: str, columns: list[str], run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame(columns=columns)
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return pd.DataFrame(columns=columns)
            sql = f"SELECT * FROM {table}"
            params = []
            if run_id is not None and table != "paper_cost_diagnostics_runs":
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            df = pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def load_cost_diagnostics_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_cost_diagnostics_runs", RUN_COLUMNS, limit=limit)


def load_cost_diagnostics_by_ticker(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_cost_diagnostics_by_ticker", BY_TICKER_COLUMNS, run_id=run_id, limit=limit)


def load_cost_diagnostics_by_signal_source(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_cost_diagnostics_by_signal_source", BY_SOURCE_COLUMNS, run_id=run_id, limit=limit)


def load_turnover_diagnostics(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_turnover_diagnostics", TURNOVER_COLUMNS, run_id=run_id, limit=limit)


def load_cost_breakeven(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_cost_breakeven", BREAKEVEN_COLUMNS, run_id=run_id, limit=limit)
