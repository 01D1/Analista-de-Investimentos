"""
test_financial_db_schema.py
Tests for financial_* table schema in src/ingestion/db.py.
Covers D-01, D-02, D-04 requirements.
"""
from __future__ import annotations

import sqlite3
import uuid

import pytest


def test_financial_tables_created(tmp_path):
    """init_db() creates all four financial_* tables."""
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

    assert {"financial_ltm", "financial_multiples", "financial_dcf", "financial_signals"}.issubset(tables)


def test_financial_ltm_columns(tmp_path):
    """financial_ltm has all required columns."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)

    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(financial_ltm)").fetchall()}
    conn.close()

    required = {
        "id", "ticker", "computed_date",
        "net_revenue", "ebitda", "net_income", "fcf",
        "net_debt", "ltm_quarters_used", "ltm_reconciliation_warning",
        "shares_outstanding", "ingested_at",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_insert_or_replace_dedup(tmp_path):
    """INSERT OR REPLACE on (ticker, computed_date) — last write wins."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)

    conn = sqlite3.connect(db)
    now = "2026-05-11T00:00:00"

    # First insert — net_revenue=1000.0
    conn.execute(
        """INSERT OR REPLACE INTO financial_ltm
           (id, ticker, computed_date, net_revenue, ltm_reconciliation_warning, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), "PETR4", "2026-05-11", 1000.0, 0, now),
    )
    conn.commit()

    # Second insert — same ticker+computed_date, different net_revenue
    conn.execute(
        """INSERT OR REPLACE INTO financial_ltm
           (id, ticker, computed_date, net_revenue, ltm_reconciliation_warning, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), "PETR4", "2026-05-11", 2000.0, 0, now),
    )
    conn.commit()

    row = conn.execute(
        "SELECT COUNT(*) as cnt, net_revenue FROM financial_ltm WHERE ticker='PETR4' AND computed_date='2026-05-11'"
    ).fetchone()
    conn.close()

    assert row[0] == 1, f"Expected 1 row (dedup), got {row[0]}"
    assert row[1] == 2000.0, f"Expected net_revenue=2000.0 (last write wins), got {row[1]}"
