"""
test_financial_engine.py
Tests for src/financial_engine.py — FIN-01 LTM aggregation, AccountMapper wire-up.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------

_FULL_SCHEMA = """
CREATE TABLE cvm_statements (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    cvm_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    period_type TEXT NOT NULL,
    account_code TEXT,
    account_name TEXT,
    normalized_name TEXT,
    value REAL,
    reference_date TEXT,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_cvm_dedup
    ON cvm_statements(ticker, period_type, year, account_code, reference_date);

CREATE TABLE macro_series (
    id TEXT PRIMARY KEY,
    series_code INTEGER NOT NULL,
    series_name TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_macro_dedup ON macro_series(series_code, date);

CREATE TABLE price_ohlcv (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    adj_close REAL, volume INTEGER,
    is_gap INTEGER DEFAULT 0,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_price_dedup ON price_ohlcv(ticker, date);

CREATE TABLE financial_ltm (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    computed_date TEXT NOT NULL,
    net_revenue REAL, ebitda REAL, net_income REAL, fcf REAL,
    net_debt REAL, gross_debt REAL, cash REAL,
    shareholders_equity REAL, shares_outstanding REAL,
    ltm_quarters_used INTEGER,
    ltm_reconciliation_warning INTEGER DEFAULT 0,
    ltm_warning_detail TEXT,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_ltm_dedup ON financial_ltm(ticker, computed_date);

CREATE TABLE financial_multiples (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    price REAL, market_cap REAL, pe_ratio REAL, ev_ebitda REAL,
    pb_ratio REAL, dividend_yield REAL, ev_revenue REAL,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_multiples_dedup ON financial_multiples(ticker, computed_date);

CREATE TABLE financial_dcf (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    valuation_method TEXT, fair_value_brl REAL, upside_pct REAL,
    wacc REAL, terminal_growth REAL, selic_used REAL, cds_used REAL,
    used_fallback INTEGER DEFAULT 0, confidence_flag TEXT,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_dcf_dedup ON financial_dcf(ticker, computed_date);

CREATE TABLE financial_signals (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    rsi_14 REAL, macd_line REAL, macd_signal REAL, macd_histogram REAL,
    ma_50 REAL, ma_200 REAL, golden_cross INTEGER, death_cross INTEGER,
    momentum_score INTEGER, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_signals_dedup ON financial_signals(ticker, computed_date);
"""


def make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_FULL_SCHEMA)
    return conn


def _insert_itr_row(conn, ticker, ref_date, year, normalized_name, value):
    """Helper: insert a single ITR row into cvm_statements."""
    conn.execute(
        """INSERT OR IGNORE INTO cvm_statements
           (id, ticker, cvm_code, year, period_type, account_code, account_name,
            normalized_name, value, reference_date, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), ticker, "000000", year, "ITR",
            "3.01", normalized_name, normalized_name, value, ref_date,
            "2026-01-01T00:00:00",
        ),
    )
    conn.commit()


def _insert_dfp_row(conn, ticker, ref_date, year, normalized_name, value):
    """Helper: insert a single DFP row into cvm_statements."""
    conn.execute(
        """INSERT OR IGNORE INTO cvm_statements
           (id, ticker, cvm_code, year, period_type, account_code, account_name,
            normalized_name, value, reference_date, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), ticker, "000000", year, "DFP",
            "3.01", normalized_name, normalized_name, value, ref_date,
            "2026-01-01T00:00:00",
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Test 1: LTM aggregates four quarters
# ---------------------------------------------------------------------------

def test_ltm_aggregates_four_quarters():
    """_aggregate_ltm() sums net_revenue across 4 ITR quarters."""
    from src.financial_engine import _aggregate_ltm

    conn = make_db()
    quarters = [
        ("2025-09-30", 2025, 100.0),
        ("2025-06-30", 2025, 200.0),
        ("2025-03-31", 2025, 150.0),
        ("2024-12-31", 2024, 250.0),
    ]
    for ref_date, year, val in quarters:
        _insert_itr_row(conn, "PETR4", ref_date, year, "net_revenue", val)

    result = _aggregate_ltm("PETR4", conn, is_bank=False)

    assert result["net_revenue"] == pytest.approx(700.0), (
        f"Expected 700.0, got {result['net_revenue']}"
    )
    assert result["ltm_quarters_used"] == 4


# ---------------------------------------------------------------------------
# Test 2: LTM DFP reconciliation warning (divergence > 5%)
# ---------------------------------------------------------------------------

def test_ltm_dfp_reconciliation_warning():
    """_check_dfp_reconciliation() returns warning_flag=1 when divergence > 5%."""
    from src.financial_engine import _check_dfp_reconciliation

    conn = make_db()
    # DFP revenue = 500.0; LTM = 700.0 → divergence = 40% > 5%
    _insert_dfp_row(conn, "PETR4", "2024-12-31", 2024, "net_revenue", 500.0)

    flag, detail = _check_dfp_reconciliation("PETR4", conn, ltm_revenue=700.0)

    assert flag == 1, f"Expected warning flag=1, got {flag}"
    assert detail is not None
    assert "div=" in detail


# ---------------------------------------------------------------------------
# Test 3: No warning when divergence within threshold
# ---------------------------------------------------------------------------

def test_ltm_no_warning_within_threshold():
    """_check_dfp_reconciliation() returns (0, None) when divergence <= 5%."""
    from src.financial_engine import _check_dfp_reconciliation

    conn = make_db()
    # DFP = 980.0; LTM = 1000.0 → divergence = 2.04% < 5%
    _insert_dfp_row(conn, "VALE3", "2024-12-31", 2024, "net_revenue", 980.0)

    flag, detail = _check_dfp_reconciliation("VALE3", conn, ltm_revenue=1000.0)

    assert flag == 0
    assert detail is None


# ---------------------------------------------------------------------------
# Test 4: Bank ticker EBITDA must be None
# ---------------------------------------------------------------------------

def test_bank_ticker_ebitda_is_none():
    """_aggregate_ltm() sets ebitda=None for bank tickers (Pitfall 2)."""
    from src.financial_engine import _aggregate_ltm

    conn = make_db()
    # Insert some ITR rows with ebit for bank ticker
    quarters = [
        ("2025-09-30", 2025, 50.0),
        ("2025-06-30", 2025, 60.0),
        ("2025-03-31", 2025, 55.0),
        ("2024-12-31", 2024, 70.0),
    ]
    for ref_date, year, val in quarters:
        _insert_itr_row(conn, "ITUB4", ref_date, year, "ebit", val)

    result = _aggregate_ltm("ITUB4", conn, is_bank=True)

    assert result.get("ebitda") is None, (
        f"Expected ebitda=None for bank ticker, got {result.get('ebitda')}"
    )


# ---------------------------------------------------------------------------
# Test 5: AccountMapper wired in cvm_downloader
# ---------------------------------------------------------------------------

def test_account_mapper_wired_in_downloader(monkeypatch, tmp_path):
    """parse_and_store() populates normalized_name via AccountMapper (not None)."""
    import pandas as pd
    from src.ingestion.cvm_downloader import CVMDownloader
    from src.ingestion.db import init_db, get_connection

    db_path = tmp_path / "ingestion.db"
    init_db(db_path)
    conn = get_connection(db_path)

    # Monkeypatch AccountMapper._map_row to always return "net_revenue"
    monkeypatch.setattr(
        "src.normalization.account_mapper.AccountMapper._map_row",
        lambda self, row: "net_revenue",
    )

    # Monkeypatch CVMDownloader to avoid actual CVM HTTP calls
    dl = CVMDownloader.__new__(CVMDownloader)
    dl.output_dir = tmp_path / "cvm"
    dl.timeout = 10
    dl.session = MagicMock()
    dl.get_cvm_code = lambda t: "000000"

    # Build a minimal CSV-like DataFrame and mock download methods
    raw_csv = tmp_path / "cvm" / "DFP" / "2024"
    raw_csv.mkdir(parents=True, exist_ok=True)

    # Create a fake DFP CSV with required columns
    df_fake = pd.DataFrame([{
        "CD_CVM": "000000",
        "CD_CONTA": "3.01",
        "DS_CONTA": "Receita Líquida",
        "VL_CONTA": "1000.0",
        "ESCALA_MOEDA": "UNIDADE",
        "DT_FIM_EXERC": "2024-12-31",
        "VERSAO": "1",
    }])
    csv_file = raw_csv / "dfp_test.csv"
    df_fake.to_csv(csv_file, sep=";", index=False)

    monkeypatch.setattr(dl, "download_dfp", lambda year, force=False: [csv_file])

    count = dl.parse_and_store(
        ticker="PETR4",
        year=2024,
        period_type="DFP",
        conn=conn,
        raw_dir=tmp_path / "cvm",
    )

    # Verify that the inserted row has normalized_name = "net_revenue" (not None)
    row = conn.execute(
        "SELECT normalized_name FROM cvm_statements LIMIT 1"
    ).fetchone()
    conn.close()

    assert row is not None, "No row inserted"
    assert row["normalized_name"] == "net_revenue", (
        f"Expected 'net_revenue', got {row['normalized_name']!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: backfill_normalized_names updates NULL rows
# ---------------------------------------------------------------------------

def test_normalized_name_backfill(monkeypatch):
    """backfill_normalized_names() fills NULL normalized_name rows."""
    from src.financial_engine import backfill_normalized_names

    conn = make_db()
    now = "2026-01-01T00:00:00"

    # Insert 3 rows with normalized_name=None (different account_codes to avoid UNIQUE constraint)
    for i, acct in enumerate(["3.01", "3.02", "3.03"]):
        conn.execute(
            """INSERT INTO cvm_statements
               (id, ticker, cvm_code, year, period_type, account_code, account_name,
                normalized_name, value, reference_date, ingested_at)
               VALUES (?, 'PETR4', '000000', 2024, 'ITR', ?, 'Receita', NULL, 100.0, '2024-09-30', ?)""",
            (str(uuid.uuid4()), acct, now),
        )
    conn.commit()

    # Monkeypatch _map_row to return "ebit"
    monkeypatch.setattr(
        "src.normalization.account_mapper.AccountMapper._map_row",
        lambda self, row: "ebit",
    )

    updated = backfill_normalized_names(conn)

    assert updated == 3, f"Expected 3 rows updated, got {updated}"

    rows = conn.execute(
        "SELECT normalized_name FROM cvm_statements WHERE ticker='PETR4'"
    ).fetchall()
    for row in rows:
        assert row["normalized_name"] == "ebit", (
            f"Expected 'ebit', got {row['normalized_name']!r}"
        )


# ---------------------------------------------------------------------------
# Test 7: FIN-02 — Industrial multiples computed correctly
# ---------------------------------------------------------------------------

def test_industrial_multiples_computed(monkeypatch):
    """_compute_multiples() writes financial_multiples row for industrial ticker with price."""
    from src.financial_engine import _compute_multiples
    from unittest.mock import MagicMock

    conn = make_db()

    # Insert price_ohlcv row for PETR4
    conn.execute(
        """INSERT INTO price_ohlcv
           (id, ticker, date, adj_close, is_gap, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), "PETR4", "2026-05-11", 35.50, 0, "2026-05-11T00:00:00"),
    )
    conn.commit()

    # LTM dict with enough data to compute multiples
    ltm = {
        "net_income": 5000.0,
        "total_equity": 25000.0,
        "ebitda": 8000.0,
        "net_revenue": 20000.0,
        "net_debt": 10000.0,
        "shares_outstanding": 1000.0,
        "dividends_paid": 500.0,
        "ebit": 7000.0,
        "gross_debt": 15000.0,
        "cash": 5000.0,
    }

    # Mock SectorConfig — industrial ticker
    mock_cfg = MagicMock()
    mock_cfg.is_bank_model = False

    _compute_multiples("PETR4", conn, ltm, mock_cfg, "2026-05-11")

    row = conn.execute(
        "SELECT * FROM financial_multiples WHERE ticker = 'PETR4'"
    ).fetchone()

    assert row is not None, "Nenhuma linha inserida em financial_multiples"
    assert row["price"] == pytest.approx(35.50), (
        f"Expected price=35.50, got {row['price']}"
    )
    assert row["pe_ratio"] is not None, "pe_ratio should not be None for industrial ticker"
    assert row["pe_ratio"] > 0, f"pe_ratio should be > 0, got {row['pe_ratio']}"


# ---------------------------------------------------------------------------
# Test 8: FIN-02 — Missing price produces flagged NULL record (no crash)
# ---------------------------------------------------------------------------

def test_multiples_handles_missing_price(monkeypatch):
    """_compute_multiples() writes NULL price row when no price in price_ohlcv — no crash."""
    from src.financial_engine import _compute_multiples
    from unittest.mock import MagicMock

    conn = make_db()

    # NO price_ohlcv rows for VALE3 — _get_current_price() must return None
    mock_cfg = MagicMock()
    mock_cfg.is_bank_model = False

    # _compute_multiples must not raise — it should write a flagged row
    _compute_multiples("VALE3", conn, {}, mock_cfg, "2026-05-11")

    row = conn.execute(
        "SELECT * FROM financial_multiples WHERE ticker = 'VALE3'"
    ).fetchone()

    assert row is not None, "Nenhuma linha inserida mesmo sem preço"
    assert row["price"] is None, f"Expected price=None, got {row['price']}"
    assert row["pe_ratio"] is None, f"Expected pe_ratio=None, got {row['pe_ratio']}"


# ---------------------------------------------------------------------------
# Test 9: FIN-02 — Bank multiples have ev_ebitda = NULL
# ---------------------------------------------------------------------------

def test_bank_multiples_ev_ebitda_null(monkeypatch):
    """_compute_multiples() writes ev_ebitda=NULL for bank tickers (FIN-05 guard)."""
    from src.financial_engine import _compute_multiples
    from unittest.mock import MagicMock

    conn = make_db()

    # Insert price_ohlcv row for ITUB4
    conn.execute(
        """INSERT INTO price_ohlcv
           (id, ticker, date, adj_close, is_gap, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), "ITUB4", "2026-05-11", 25.0, 0, "2026-05-11T00:00:00"),
    )
    conn.commit()

    # LTM dict for bank ticker
    ltm = {
        "net_income": 3000.0,
        "total_equity": 20000.0,
        "shares_outstanding": 800.0,
        "nii_gross": 5000.0,
        "fee_income": 1000.0,
        "loan_portfolio_gross": 60000.0,
        "total_assets": 100000.0,
    }

    # Mock SectorConfig — bank ticker
    mock_bank_cfg = MagicMock()
    mock_bank_cfg.is_bank_model = True

    _compute_multiples("ITUB4", conn, ltm, mock_bank_cfg, "2026-05-11")

    row = conn.execute(
        "SELECT * FROM financial_multiples WHERE ticker = 'ITUB4'"
    ).fetchone()

    assert row is not None, "Nenhuma linha inserida para ITUB4"
    assert row["ev_ebitda"] is None, (
        f"Expected ev_ebitda=NULL for bank ticker, got {row['ev_ebitda']}"
    )
    assert row["pe_ratio"] is not None, (
        f"Expected pe_ratio not None for bank with price and net_income, got {row['pe_ratio']}"
    )
