"""Persistência do paper trading."""
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
    "capital_initial",
    "capital_final",
    "total_return",
    "sharpe",
    "sortino",
    "max_drawdown",
    "trades_count",
    "win_rate",
    "profit_factor",
    "governance_status",
    "metadata_json",
]

ORDER_COLUMNS = [
    "run_id",
    "created_at",
    "trade_date",
    "ticker",
    "side",
    "quantity",
    "theoretical_price",
    "simulated_execution_price",
    "execution_cost",
    "slippage_cost",
    "order_status",
    "signal_source",
    "rejection_reason",
    "normalized_order_reason",
    "reason_confidence",
    "cost_bucket",
    "lifecycle_id",
    "parent_signal_id",
    "parent_position_id",
    "is_simulation_end_close",
    "metadata_json",
]

POSITION_COLUMNS = [
    "run_id",
    "trade_date",
    "ticker",
    "quantity",
    "avg_price",
    "market_price",
    "market_value",
    "unrealized_pnl",
    "realized_pnl",
    "var_95",
    "expected_shortfall_95",
    "metadata_json",
]

EQUITY_COLUMNS = [
    "run_id",
    "trade_date",
    "cash",
    "equity",
    "exposure",
    "daily_return",
    "drawdown",
    "portfolio_var_95",
    "portfolio_es_95",
    "metadata_json",
]

EXIT_EVENT_COLUMNS = [
    "run_id",
    "trade_date",
    "ticker",
    "position_id",
    "exit_rule_triggered",
    "exit_reason",
    "exit_price",
    "pnl",
    "metadata_json",
]

REBALANCE_EVENT_COLUMNS = [
    "run_id",
    "trade_date",
    "ticker",
    "action",
    "current_weight",
    "target_weight",
    "order_quantity",
    "reason",
    "metadata_json",
]

PNL_ATTRIBUTION_COLUMNS = [
    "run_id",
    "attribution_type",
    "bucket",
    "trades",
    "gross_pnl",
    "net_pnl",
    "win_rate",
    "avg_return",
    "contribution_pct",
    "metadata_json",
]


def _save_table(db_path: str | Path, table: str, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        df.to_sql(table, con, if_exists="append", index=False)
    return int(len(df))


def save_paper_simulation_run(
    db_path: str | Path,
    run_summary: dict,
    orders_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    equity_curve_df: pd.DataFrame,
    exit_events_df: pd.DataFrame | None = None,
    rebalance_events_df: pd.DataFrame | None = None,
    pnl_attribution_df: pd.DataFrame | None = None,
) -> int:
    init_database(db_path, verbose=False)
    now = datetime.utcnow().isoformat(timespec="seconds")
    row = {col: run_summary.get(col) for col in RUN_COLUMNS}
    row["started_at"] = row.get("started_at") or now
    row["finished_at"] = row.get("finished_at") or now
    row["metadata_json"] = row.get("metadata_json") or json.dumps(run_summary.get("metadata", {}), ensure_ascii=False)
    run_df = pd.DataFrame([row], columns=RUN_COLUMNS)
    with sqlite3.connect(db_path) as con:
        run_df.to_sql("paper_simulation_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
    specs = [
        (orders_df, "paper_orders", ORDER_COLUMNS),
        (positions_df, "paper_positions", POSITION_COLUMNS),
        (equity_curve_df, "paper_equity_curve", EQUITY_COLUMNS),
        (exit_events_df, "paper_exit_events", EXIT_EVENT_COLUMNS),
        (rebalance_events_df, "paper_rebalance_events", REBALANCE_EVENT_COLUMNS),
        (pnl_attribution_df, "paper_pnl_attribution", PNL_ATTRIBUTION_COLUMNS),
    ]
    for df, table, columns in specs:
        if df is not None and not df.empty:
            save = df.copy()
            save["run_id"] = run_id
            for col in columns:
                if col not in save.columns:
                    save[col] = pd.NA
            save = save[columns]
            _save_table(db_path, table, save)
    return run_id


def _read(db_path: str | Path, table: str, run_id: int | None = None, limit: int = 500) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return pd.DataFrame()
            sql = f"SELECT * FROM {table}"
            params = []
            if run_id is not None and table != "paper_simulation_runs":
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame()


def load_paper_simulation_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_simulation_runs", limit=limit)


def load_paper_orders(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_orders", run_id=run_id, limit=5000)


def load_paper_positions(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_positions", run_id=run_id, limit=5000)


def load_paper_equity_curve(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_equity_curve", run_id=run_id, limit=5000)


def load_paper_exit_events(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_exit_events", run_id=run_id, limit=5000)


def load_paper_rebalance_events(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_rebalance_events", run_id=run_id, limit=5000)


def load_paper_pnl_attribution(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_pnl_attribution", run_id=run_id, limit=5000)
