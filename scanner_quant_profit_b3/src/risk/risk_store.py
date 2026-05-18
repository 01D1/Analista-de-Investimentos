"""Persistencia do Risk Engine."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RISK_SNAPSHOT_COLUMNS = [
    "created_at",
    "trade_date",
    "ticker",
    "price",
    "position_value",
    "ensemble_vol",
    "volatility_regime",
    "parametric_var_95",
    "historical_var_95",
    "expected_shortfall_95",
    "recommended_size",
    "recommended_position_value",
    "limiting_factor",
    "risk_status",
    "explanation",
    "metadata_json",
]


def _save(db_path: str | Path, table: str, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        df.to_sql(table, con, if_exists="append", index=False)
    return len(df)


def save_volatility_estimates(db_path, df): return _save(db_path, "volatility_estimates", df)
def save_risk_snapshots(db_path, df): return _save(db_path, "risk_snapshots", df)
def save_var_estimates(db_path, df): return _save(db_path, "var_estimates", df)
def save_position_sizing_snapshots(db_path, df): return _save(db_path, "position_sizing_snapshots", df)
def save_stress_test_results(db_path, df): return _save(db_path, "stress_test_results", df)
def save_risk_governance_reviews(db_path, df): return _save(db_path, "risk_governance_reviews", df)


def load_latest_risk_snapshots(db_path: str | Path, tickers: list[str] | None = None) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=RISK_SNAPSHOT_COLUMNS)
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='risk_snapshots'").fetchone() is None:
                return pd.DataFrame(columns=RISK_SNAPSHOT_COLUMNS)
            df = pd.read_sql_query("SELECT * FROM risk_snapshots ORDER BY created_at DESC, id DESC", con)
        if df.empty:
            return df
        df = df.sort_values(["ticker", "created_at"], ascending=[True, False]).groupby("ticker", as_index=False).first()
        if tickers:
            allowed = {t.upper() for t in tickers}
            df = df[df["ticker"].astype(str).str.upper().isin(allowed)].copy()
        return df
    except Exception:
        return pd.DataFrame(columns=RISK_SNAPSHOT_COLUMNS)


def load_risk_history(db_path: str | Path, ticker: str | None = None, limit: int = 500) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=RISK_SNAPSHOT_COLUMNS)
    try:
        with sqlite3.connect(db_path) as con:
            sql = "SELECT * FROM risk_snapshots"
            params = []
            if ticker:
                sql += " WHERE ticker = ?"
                params.append(ticker.upper())
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame(columns=RISK_SNAPSHOT_COLUMNS)

