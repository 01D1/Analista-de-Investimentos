"""Histórico de snapshots da cadeia de opções."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


HISTORY_COLUMNS = [
    "trade_date",
    "captured_at",
    "option_ticker",
    "underlying",
    "option_type",
    "strike",
    "maturity_date",
    "days_to_maturity",
    "last_price",
    "bid",
    "ask",
    "spread_pct",
    "volume",
    "trades",
    "financial_volume",
    "open_interest",
    "underlying_price",
    "moneyness_pct",
    "moneyness_class",
    "intrinsic_value",
    "extrinsic_value",
    "breakeven",
    "implied_volatility",
    "historical_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "liquidity_score",
    "risk_score",
]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=HISTORY_COLUMNS)


def load_options_chain_snapshots(
    db_path: str | Path,
    start_date: str | None = None,
    end_date: str | None = None,
    underlyings: list[str] | None = None,
) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return _empty()
    where = []
    params: list[Any] = []
    if start_date:
        where.append("trade_date >= ?")
        params.append(start_date)
    if end_date:
        where.append("trade_date <= ?")
        params.append(end_date)
    if underlyings:
        clean = [u.upper() for u in underlyings]
        where.append("upper(underlying) IN (" + ",".join("?" for _ in clean) + ")")
        params.extend(clean)
    sql = "SELECT * FROM options_chain_snapshots"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY trade_date, underlying, maturity_date, strike, option_ticker, captured_at"
    try:
        with sqlite3.connect(path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_chain_snapshots'").fetchone()
            if not exists:
                return _empty()
            df = pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return _empty()
    if df.empty:
        return _empty()
    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[HISTORY_COLUMNS]


def create_daily_chain_view(chain_df: pd.DataFrame) -> pd.DataFrame:
    if chain_df is None or chain_df.empty:
        return _empty()
    work = chain_df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    work["captured_sort"] = pd.to_datetime(work.get("captured_at"), errors="coerce")
    work = work.sort_values(["trade_date", "option_ticker", "captured_sort"])
    work = work.drop_duplicates(["trade_date", "option_ticker"], keep="last")
    work = work.drop(columns=["captured_sort"], errors="ignore")
    sort_cols = [c for c in ["trade_date", "underlying", "maturity_date", "strike", "option_ticker"] if c in work.columns]
    return work.sort_values(sort_cols).reset_index(drop=True)


def get_chain_for_date(
    chain_df: pd.DataFrame,
    trade_date: str,
    underlying: str | None = None,
    maturity_date: str | None = None,
) -> pd.DataFrame:
    daily = create_daily_chain_view(chain_df)
    if daily.empty:
        return daily
    out = daily[daily["trade_date"].astype(str) == str(trade_date)].copy()
    if underlying:
        out = out[out["underlying"].astype(str).str.upper() == underlying.upper()]
    if maturity_date:
        out = out[out["maturity_date"].astype(str) == str(maturity_date)]
    return out.reset_index(drop=True)


def get_available_option_history_range(db_path: str | Path) -> dict[str, Any]:
    df = load_options_chain_snapshots(db_path)
    if df.empty:
        return {
            "min_date": None,
            "max_date": None,
            "underlyings_count": 0,
            "options_count": 0,
            "snapshots_count": 0,
            "coverage_status": "SEM_DADOS",
        }
    dates = pd.to_datetime(df["trade_date"], errors="coerce").dropna()
    days = dates.dt.date.nunique()
    options = df["option_ticker"].dropna().nunique()
    underlyings = df["underlying"].dropna().nunique()
    if days >= 60 and options >= 100:
        status = "COBERTURA_BOA"
    elif days >= 20 and options >= 30:
        status = "COBERTURA_MEDIA"
    else:
        status = "COBERTURA_FRACA"
    return {
        "min_date": str(dates.min().date()) if not dates.empty else None,
        "max_date": str(dates.max().date()) if not dates.empty else None,
        "underlyings_count": int(underlyings),
        "options_count": int(options),
        "snapshots_count": int(len(df)),
        "coverage_status": status,
    }

