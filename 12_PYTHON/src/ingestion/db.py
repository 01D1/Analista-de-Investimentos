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

CREATE TABLE IF NOT EXISTS financial_ltm (
    id                          TEXT PRIMARY KEY,
    ticker                      TEXT NOT NULL,
    computed_date               TEXT NOT NULL,
    net_revenue                 REAL,
    ebitda                      REAL,
    net_income                  REAL,
    fcf                         REAL,
    net_debt                    REAL,
    gross_debt                  REAL,
    cash                        REAL,
    shareholders_equity         REAL,
    shares_outstanding          REAL,
    ltm_quarters_used           INTEGER,
    ltm_reconciliation_warning  INTEGER DEFAULT 0,
    ltm_warning_detail          TEXT,
    ingested_at                 TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ltm_dedup ON financial_ltm(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_multiples (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    computed_date   TEXT NOT NULL,
    price           REAL,
    market_cap      REAL,
    pe_ratio        REAL,
    ev_ebitda       REAL,
    pb_ratio        REAL,
    dividend_yield  REAL,
    ev_revenue      REAL,
    ingested_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_multiples_dedup ON financial_multiples(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_dcf (
    id                  TEXT PRIMARY KEY,
    ticker              TEXT NOT NULL,
    computed_date       TEXT NOT NULL,
    valuation_method    TEXT,
    fair_value_brl      REAL,
    upside_pct          REAL,
    wacc                REAL,
    terminal_growth     REAL,
    selic_used          REAL,
    cds_used            REAL,
    used_fallback       INTEGER DEFAULT 0,
    confidence_flag     TEXT,
    ingested_at         TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dcf_dedup ON financial_dcf(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_signals (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    computed_date   TEXT NOT NULL,
    rsi_14          REAL,
    macd_line       REAL,
    macd_signal     REAL,
    macd_histogram  REAL,
    ma_50           REAL,
    ma_200          REAL,
    golden_cross    INTEGER,
    death_cross     INTEGER,
    momentum_score  INTEGER,
    ingested_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_dedup ON financial_signals(ticker, computed_date);

CREATE TABLE IF NOT EXISTS thesis_versions (
    id                 TEXT PRIMARY KEY,
    ticker             TEXT NOT NULL,
    version_num        INTEGER NOT NULL,
    generated_at       TEXT NOT NULL,
    input_hash         TEXT NOT NULL,
    positioning        TEXT NOT NULL,
    confidence         TEXT NOT NULL,
    fair_value_brl     REAL NOT NULL,
    dcf_deviation_flag INTEGER DEFAULT 0,
    thesis_json        TEXT NOT NULL,
    diff_summary       TEXT,
    UNIQUE(ticker, version_num)
);
CREATE INDEX IF NOT EXISTS idx_thesis_ticker ON thesis_versions(ticker);
CREATE INDEX IF NOT EXISTS idx_thesis_hash   ON thesis_versions(ticker, input_hash);

CREATE TABLE IF NOT EXISTS opportunity_signals (
    id               TEXT PRIMARY KEY,
    ticker           TEXT NOT NULL,
    computed_date    TEXT NOT NULL,
    signal_type      TEXT NOT NULL,
    description      TEXT NOT NULL,
    conviction_score INTEGER NOT NULL,
    ingested_at      TEXT NOT NULL,
    UNIQUE(ticker, computed_date, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON opportunity_signals(ticker);

CREATE VIEW IF NOT EXISTS thesis_latest AS
SELECT * FROM thesis_versions
WHERE (ticker, version_num) IN (
    SELECT ticker, MAX(version_num)
    FROM thesis_versions
    GROUP BY ticker
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """Cria as tabelas do ingestion.db se ainda não existirem. Idempotente."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    # WR-01: WAL mode allows concurrent readers while writing; busy_timeout avoids
    # immediate "database is locked" errors when two jobs overlap (e.g. b3_prices
    # still running when cvm_ingest starts — 5 s grace period before failing).
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_CREATE_SQL)
    conn.commit()
    conn.close()
    log.debug(f"[db] init_db complete — {db_path}")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Retorna conexão sqlite3 aberta com row_factory=sqlite3.Row.

    CR-05: busy_timeout=5000 is a per-connection setting; re-apply here so that
    every caller gets the same 5 s grace period before 'database is locked' errors,
    matching the PRAGMA set in init_db().
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")  # match init_db setting
    return conn
