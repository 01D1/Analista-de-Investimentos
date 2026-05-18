"""Helpers SQLite para conectores defensivos."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def empty(columns: list[str], message: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(columns=columns)
    if message:
        df.attrs["mensagem"] = message
    return df


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def read_table(db_path: str | Path, table: str, columns: list[str], order_by: str = "", where: str = "", params: tuple | None = None, limit: int | None = None) -> pd.DataFrame:
    if not Path(db_path).exists():
        return empty(columns, f"Banco nao encontrado: {db_path}")
    try:
        with sqlite3.connect(db_path) as con:
            if not table_exists(con, table):
                return empty(columns, f"Tabela ausente: {table}")
            existing = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
            select_cols = [c for c in columns if c in existing]
            if not select_cols:
                return empty(columns, f"Tabela sem colunas esperadas: {table}")
            sql = f"SELECT {', '.join(select_cols)} FROM {table}"
            if where:
                sql += f" WHERE {where}"
            if order_by:
                sql += f" ORDER BY {order_by}"
            if limit:
                sql += f" LIMIT {int(limit)}"
            df = pd.read_sql_query(sql, con, params=params or ())
    except sqlite3.Error as exc:
        return empty(columns, f"Erro ao ler {table}: {exc}")
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def filter_tickers(df: pd.DataFrame, tickers: list[str] | None, col: str = "ticker") -> pd.DataFrame:
    if df.empty or not tickers or col not in df.columns:
        return df
    allowed = {str(t).upper() for t in tickers}
    return df[df[col].astype(str).str.upper().isin(allowed)].copy()

