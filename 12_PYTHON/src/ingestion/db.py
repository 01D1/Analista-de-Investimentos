"""
db.py
-----
Cria e gerencia o banco de dados SQLite de ingestão (ingestion.db).

Tabelas:
  - cvm_statements  : demonstrativos CVM (DFP, ITR, IPE)
  - macro_series    : séries macro do BCB/SGS
  - price_ohlcv     : preços OHLCV da B3 via yfinance
  - news_articles   : notícias e artigos coletados

Uso:
    from src.ingestion.db import init_db, get_connection, DB_PATH

    init_db()                       # cria tabelas (idempotente)
    conn = get_connection()         # abre conexão com row_factory=sqlite3.Row
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "ingestion.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS cvm_statements (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    cvm_code        TEXT NOT NULL,
    year            INTEGER NOT NULL,
    period_type     TEXT NOT NULL,
    account_code    TEXT,
    account_name    TEXT,
    normalized_name TEXT,
    value           REAL,
    reference_date  TEXT,
    ingested_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cvm_ticker   ON cvm_statements(ticker);
CREATE INDEX IF NOT EXISTS idx_cvm_period   ON cvm_statements(period_type, year);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cvm_dedup
    ON cvm_statements(ticker, period_type, year, account_code, reference_date);

CREATE TABLE IF NOT EXISTS macro_series (
    id          TEXT PRIMARY KEY,
    series_code INTEGER NOT NULL,
    series_name TEXT NOT NULL,
    date        TEXT NOT NULL,
    value       REAL NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_dedup ON macro_series(series_code, date);

CREATE TABLE IF NOT EXISTS price_ohlcv (
    id          TEXT PRIMARY KEY,
    ticker      TEXT NOT NULL,
    date        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    adj_close   REAL,
    volume      INTEGER,
    is_gap      INTEGER DEFAULT 0,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_price_dedup ON price_ohlcv(ticker, date);
CREATE INDEX IF NOT EXISTS idx_price_ticker ON price_ohlcv(ticker);

CREATE TABLE IF NOT EXISTS news_articles (
    id           TEXT PRIMARY KEY,
    url          TEXT NOT NULL,
    title        TEXT NOT NULL,
    published_at TEXT,
    source       TEXT,
    ticker_tags  TEXT,
    score        INTEGER DEFAULT 0,
    ingested_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_url ON news_articles(url);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """Cria as tabelas do ingestion.db se ainda não existirem. Idempotente."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_CREATE_SQL)
    conn.commit()
    conn.close()
    log.debug(f"[db] init_db complete — {db_path}")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Retorna conexão sqlite3 aberta com row_factory=sqlite3.Row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
