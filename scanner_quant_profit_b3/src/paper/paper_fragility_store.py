"""Persistencia do diagnostico de fragilidade do paper trading."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = ["created_at", "source_run_id", "status", "total_trades", "total_net_pnl", "fragility_score", "fragility_class", "governance_status", "metadata_json"]
ASSET_COLUMNS = ["run_id", "ticker", "trades_count", "net_pnl", "win_rate", "contribution_pct", "cost_drag", "drawdown_contribution", "fragility_score", "fragility_class", "metadata_json"]
SOURCE_COLUMNS = ["run_id", "signal_source", "trades_count", "net_pnl", "win_rate", "contribution_pct", "cost_drag", "fragility_score", "fragility_class", "metadata_json"]
DRAWDOWN_COLUMNS = ["run_id", "drawdown_start", "drawdown_trough", "drawdown_recovery", "depth", "duration_days", "recovered", "metadata_json"]


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _prepare(df: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    out = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns]


def save_paper_fragility_run(
    db_path: str | Path,
    summary: dict,
    asset_df: pd.DataFrame,
    signal_source_df: pd.DataFrame,
    drawdown_df: pd.DataFrame,
) -> int:
    init_database(db_path, verbose=False)
    row = {col: summary.get(col) for col in RUN_COLUMNS}
    row["created_at"] = row.get("created_at") or _now()
    row["metadata_json"] = row.get("metadata_json") or json.dumps(summary.get("metadata", {}), ensure_ascii=False)
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([row], columns=RUN_COLUMNS).to_sql("paper_fragility_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if asset_df is not None and not asset_df.empty:
            assets = asset_df.copy()
            assets["run_id"] = run_id
            if "cost_drag" not in assets.columns and "total_cost_drag" in assets.columns:
                assets["cost_drag"] = assets["total_cost_drag"]
            _prepare(assets, ASSET_COLUMNS).to_sql("paper_fragility_by_asset", con, if_exists="append", index=False)
        if signal_source_df is not None and not signal_source_df.empty:
            sources = signal_source_df.copy()
            sources["run_id"] = run_id
            if "trades_count" not in sources.columns and "trades" in sources.columns:
                sources["trades_count"] = sources["trades"]
            _prepare(sources, SOURCE_COLUMNS).to_sql("paper_fragility_by_signal_source", con, if_exists="append", index=False)
        if drawdown_df is not None and not drawdown_df.empty:
            dd = drawdown_df.copy()
            dd["run_id"] = run_id
            _prepare(dd, DRAWDOWN_COLUMNS).to_sql("paper_drawdown_periods", con, if_exists="append", index=False)
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
            if run_id is not None and table != "paper_fragility_runs":
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame()


def load_paper_fragility_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_fragility_runs", limit=limit)


def load_paper_fragility_by_asset(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_fragility_by_asset", run_id=run_id, limit=5000)


def load_paper_fragility_by_signal_source(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_fragility_by_signal_source", run_id=run_id, limit=5000)


def load_paper_drawdown_periods(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    return _read(db_path, "paper_drawdown_periods", run_id=run_id, limit=5000)
