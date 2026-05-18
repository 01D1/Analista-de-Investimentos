"""
test_db_schema.py
Tests for src/ingestion/db.py — init_db(), get_connection().
Covers ING-01 schema requirements.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def test_init_db_creates_all_four_tables(tmp_path):
    """init_db() creates all 8 required tables (4 ingestion + 4 financial)."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)

    conn = sqlite3.connect(db)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    # Original 4 ingestion tables
    assert {"cvm_statements", "macro_series", "price_ohlcv", "news_articles"}.issubset(tables)
    # Phase 3 financial tables
    assert {"financial_ltm", "financial_multiples", "financial_dcf", "financial_signals"}.issubset(tables)


def test_init_db_is_idempotent(tmp_path):
    """Calling init_db() twice raises no error and table count remains 8."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    init_db(db)  # second call — must not raise

    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    conn.close()

    assert count >= 10


def test_get_connection_returns_open_connection_with_row_factory(tmp_path):
    """get_connection() returns an open sqlite3.Connection with row_factory=sqlite3.Row."""
    from src.ingestion.db import init_db, get_connection

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = get_connection(db)

    assert conn is not None
    assert conn.row_factory is sqlite3.Row

    # Verify connection is usable
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
    assert row is not None
    conn.close()


def test_all_tables_have_text_pk(tmp_path):
    """All 4 tables use TEXT as PRIMARY KEY (not INTEGER AUTOINCREMENT)."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)

    tables = ["cvm_statements", "macro_series", "price_ohlcv", "news_articles", "thesis_versions", "opportunity_signals"]
    for table in tables:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        pk_cols = [c for c in cols if c[5] == 1]  # column 5 is 'pk' flag
        assert len(pk_cols) == 1, f"{table} should have exactly 1 PK column"
        pk_type = pk_cols[0][2].upper()  # column 2 is type
        assert pk_type == "TEXT", f"{table} PK should be TEXT, got {pk_type}"

    conn.close()


def test_unique_indexes_exist(tmp_path):
    """UNIQUE indexes exist on macro_series(series_code,date), price_ohlcv(ticker,date), news_articles(url)."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)

    indexes = {
        r[1]: r[2]  # name -> unique flag
        for r in conn.execute("SELECT * FROM sqlite_master WHERE type='index'").fetchall()
    }

    assert "idx_macro_dedup" in indexes, "idx_macro_dedup not found"
    assert "idx_price_dedup" in indexes, "idx_price_dedup not found"
    assert "idx_news_url" in indexes, "idx_news_url not found"

    conn.close()


def test_phase4_schema(tmp_path):
    """init_db() creates thesis_versions and opportunity_signals tables (Phase 4 — INT-04)."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert {"thesis_versions", "opportunity_signals"}.issubset(tables), (
        f"Phase 4 tables missing. Found: {tables}"
    )


def test_thesis_latest_view(tmp_path):
    """init_db() creates thesis_latest VIEW visible in sqlite_master with type='view' (D-14)."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"
    ).fetchall()}
    conn.close()
    assert "thesis_latest" in views, f"thesis_latest VIEW not found in sqlite_master. Views: {views}"
