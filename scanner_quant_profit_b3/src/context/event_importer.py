"""Importação e persistência local de eventos de mercado."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.context.event_model import EVENT_COLUMNS, normalize_event_record
from src.db.init_db import init_database


REQUIRED_CSV_COLUMNS = ["event_date", "ticker", "event_type", "event_source", "event_title"]
EXTRA_DB_COLUMNS = ["duplicate_group_id", "is_duplicate", "canonical_event_id", "coverage_source", "normalized_at"]
DB_COLUMNS = [col for col in EVENT_COLUMNS if col != "event_id"] + EXTRA_DB_COLUMNS


def _empty_events(message: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(columns=EVENT_COLUMNS + ["id"])
    if message:
        df.attrs["mensagem"] = message
    return df


def normalize_event_types(events_df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza datas, tipos, tickers e direção de impacto."""
    if events_df is None or events_df.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    rows = []
    for _, row in events_df.copy().iterrows():
        rows.append(normalize_event_record(row.to_dict()))
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)


def load_events_from_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo de eventos nao encontrado: {csv_path}")
    df = pd.read_csv(csv_path)
    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV de eventos sem colunas obrigatorias: {', '.join(missing)}")
    for col in EVENT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return normalize_event_types(df)


def save_events_to_db(events_df: pd.DataFrame, db_path: str | Path) -> int:
    base = normalize_event_types(events_df)
    events = base.copy()
    if events_df is not None:
        for col in EXTRA_DB_COLUMNS:
            if col in events_df.columns:
                events[col] = events_df[col].values
    if events.empty:
        return 0
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        sql = f"""
            INSERT INTO market_events ({', '.join(DB_COLUMNS)})
            VALUES ({', '.join(['?'] * len(DB_COLUMNS))})
        """
        for _, row in events.iterrows():
            values = []
            for col in DB_COLUMNS:
                value = row.get(col)
                if col == "metadata_json" and isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False, default=str)
                values.append(value)
            cur.execute(sql, values)
        con.commit()
    return int(len(events))


def load_events_from_db(
    db_path: str | Path,
    start_date: str | None = None,
    end_date: str | None = None,
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    if not Path(db_path).exists():
        return _empty_events(f"Banco nao encontrado: {db_path}")
    init_database(db_path, verbose=False)
    clauses = []
    params: list = []
    if start_date:
        clauses.append("event_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("event_date <= ?")
        params.append(end_date)
    if tickers:
        clean = [ticker.upper() for ticker in tickers]
        clauses.append(f"ticker IN ({', '.join(['?'] * len(clean))})")
        params.extend(clean)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query(
            f"SELECT id, {', '.join(DB_COLUMNS)} FROM market_events {where} ORDER BY event_date, ticker",
            con,
            params=params,
        )
    if df.empty:
        return _empty_events("Nenhum evento encontrado no periodo.")
    df["event_id"] = df["id"]
    return normalize_event_types(df).assign(id=df["id"].values)


def save_event_context_run(
    *,
    db_path: str | Path,
    start_date: str | None,
    end_date: str | None,
    events_count: int,
    signals_linked: int,
    tickers_count: int,
    source: str = "event_context_analysis",
    metadata: dict | None = None,
) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO event_context_runs (
                created_at, start_date, end_date, events_count, signals_linked,
                tickers_count, source, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                start_date,
                end_date,
                int(events_count),
                int(signals_linked),
                int(tickers_count),
                source,
                json.dumps(metadata or {}, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)
