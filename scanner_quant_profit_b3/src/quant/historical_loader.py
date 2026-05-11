"""Carregamento robusto de precos historicos diarios do SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd


EXPECTED_DAILY_COLUMNS = [
    "trade_date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trades",
    "quantity",
]

PRICE_TABLE_CANDIDATES = ("cotahist_daily", "market_daily", "b3_quotes")


def _empty_prices(message: str) -> pd.DataFrame:
    df = pd.DataFrame(columns=EXPECTED_DAILY_COLUMNS)
    df.attrs["mensagem"] = message
    return df


def _table_names(con: sqlite3.Connection) -> set[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _table_columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()]


def detect_available_price_tables(db_path: str | Path) -> list[dict]:
    """Lista tabelas/views candidatas a fonte de precos diarios."""
    db_path = Path(db_path)
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as con:
        names = _table_names(con)
        out = []
        for table in PRICE_TABLE_CANDIDATES:
            if table not in names:
                continue
            columns = _table_columns(con, table)
            required = {"trade_date", "ticker", "close"}
            row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            out.append(
                {
                    "table": table,
                    "columns": columns,
                    "row_count": int(row_count),
                    "usable": required.issubset(columns),
                }
            )
    return out


def _select_source_table(con: sqlite3.Connection) -> tuple[str | None, list[str]]:
    names = _table_names(con)
    for table in PRICE_TABLE_CANDIDATES:
        if table not in names:
            continue
        columns = _table_columns(con, table)
        if {"trade_date", "ticker", "close"}.issubset(columns):
            row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if row_count > 0:
                return table, columns
    return None, []


def _stock_filter(columns: Iterable[str], table: str) -> str:
    cols = set(columns)
    if "asset_type" in cols:
        return " AND (asset_type = 'ACAO' OR asset_type IS NULL)"
    if "option_type" in cols and "market_type" in cols:
        return (
            " AND (option_type IS NULL OR option_type NOT IN ('CALL', 'PUT'))"
            " AND (market_type IN ('010', '10', 10) OR market_type IS NULL)"
        )
    if "market_type" in cols:
        return " AND (market_type IN ('010', '10', 10) OR market_type IS NULL)"
    return ""


def load_daily_prices(
    db_path: str | Path,
    tickers: Iterable[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Carrega precos diarios normalizados de cotahist_daily, market_daily ou b3_quotes."""
    db_path = Path(db_path)
    if not db_path.exists():
        return _empty_prices(f"Banco nao encontrado: {db_path}")

    with sqlite3.connect(db_path) as con:
        table, columns = _select_source_table(con)
        if table is None:
            return _empty_prices("Nenhuma tabela de precos diarios com dados foi encontrada.")

        select_cols = []
        for col in EXPECTED_DAILY_COLUMNS:
            if col in columns:
                select_cols.append(col)
            else:
                select_cols.append(f"NULL AS {col}")

        query = f"SELECT {', '.join(select_cols)} FROM {table} WHERE 1=1"
        params: list[object] = []
        query += _stock_filter(columns, table)

        if tickers:
            ticker_list = [str(t).upper() for t in tickers]
            placeholders = ",".join(["?"] * len(ticker_list))
            query += f" AND UPPER(ticker) IN ({placeholders})"
            params.extend(ticker_list)
        if start_date:
            query += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND trade_date <= ?"
            params.append(end_date)
        query += " ORDER BY ticker, trade_date"

        df = pd.read_sql_query(query, con, params=params)

    if df.empty:
        out = _empty_prices("Tabela de precos encontrada, mas nenhum registro bateu os filtros.")
        out.attrs["source_table"] = table
        return out

    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.date.astype(str)
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    for col in ["open", "high", "low", "close", "volume", "trades", "quantity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["trade_date", "ticker", "close"]).reset_index(drop=True)
    df.attrs["source_table"] = table
    return df[EXPECTED_DAILY_COLUMNS]
