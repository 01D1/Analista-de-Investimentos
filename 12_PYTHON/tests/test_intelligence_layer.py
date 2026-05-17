"""
test_intelligence_layer.py
--------------------------
Phase 4 — Intelligence Layer tests covering INT-01 through INT-06.

Test strategy:
  - All tests mock instructor.from_anthropic() — no real Claude API calls.
  - In-memory SQLite DB using make_db() fixture matches full schema.
  - xfail-marked in Wave 0; marks removed as implementation lands in Plans 04-02 and 04-03.

Requirements covered:
  INT-01: IntelligenceClient + InvestmentThesis schema
  INT-02: DCF cross-check (+-10% deviation flag)
  INT-03: Hash gate + 2/day cap
  INT-04: thesis_versions write + version_num auto-increment
  INT-05: DCF_DIVERGENCE / MOMENTUM_CROSSOVER / IPE_EVENT signals
  INT-06: opportunity_signals top-3 INSERT OR REPLACE
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest

# -- Full schema for in-memory DB ---------------------------------------------

_FULL_SCHEMA = """
CREATE TABLE IF NOT EXISTS cvm_statements (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, cvm_code TEXT NOT NULL,
    year INTEGER NOT NULL, period_type TEXT NOT NULL, account_code TEXT,
    account_name TEXT, normalized_name TEXT, value REAL,
    reference_date TEXT, ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS macro_series (
    id TEXT PRIMARY KEY, series_code INTEGER NOT NULL, series_name TEXT NOT NULL,
    date TEXT NOT NULL, value REAL NOT NULL, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_dedup ON macro_series(series_code, date);
CREATE TABLE IF NOT EXISTS price_ohlcv (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, adj_close REAL,
    volume INTEGER, is_gap INTEGER DEFAULT 0, ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS news_articles (
    id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL,
    published_at TEXT, source TEXT, ticker_tags TEXT,
    score INTEGER DEFAULT 0, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_url ON news_articles(url);
CREATE TABLE IF NOT EXISTS financial_ltm (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    net_revenue REAL, ebitda REAL, net_income REAL, fcf REAL, net_debt REAL,
    gross_debt REAL, cash REAL, shareholders_equity REAL, shares_outstanding REAL,
    ltm_quarters_used INTEGER, ltm_reconciliation_warning INTEGER DEFAULT 0,
    ltm_warning_detail TEXT, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ltm_dedup ON financial_ltm(ticker, computed_date);
CREATE TABLE IF NOT EXISTS financial_multiples (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    price REAL, market_cap REAL, pe_ratio REAL, ev_ebitda REAL, pb_ratio REAL,
    dividend_yield REAL, ev_revenue REAL, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_multiples_dedup ON financial_multiples(ticker, computed_date);
CREATE TABLE IF NOT EXISTS financial_dcf (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    valuation_method TEXT, fair_value_brl REAL, upside_pct REAL, wacc REAL,
    terminal_growth REAL, selic_used REAL, cds_used REAL,
    used_fallback INTEGER DEFAULT 0, confidence_flag TEXT, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dcf_dedup ON financial_dcf(ticker, computed_date);
CREATE TABLE IF NOT EXISTS financial_signals (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    rsi_14 REAL, macd_line REAL, macd_signal REAL, macd_histogram REAL,
    ma_50 REAL, ma_200 REAL, golden_cross INTEGER, death_cross INTEGER,
    momentum_score INTEGER, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_dedup ON financial_signals(ticker, computed_date);
CREATE TABLE IF NOT EXISTS thesis_versions (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, version_num INTEGER NOT NULL,
    generated_at TEXT NOT NULL, input_hash TEXT NOT NULL, positioning TEXT NOT NULL,
    confidence TEXT NOT NULL, fair_value_brl REAL NOT NULL,
    dcf_deviation_flag INTEGER DEFAULT 0, thesis_json TEXT NOT NULL,
    diff_summary TEXT, UNIQUE(ticker, version_num)
);
CREATE INDEX IF NOT EXISTS idx_thesis_ticker ON thesis_versions(ticker);
CREATE INDEX IF NOT EXISTS idx_thesis_hash   ON thesis_versions(ticker, input_hash);
CREATE TABLE IF NOT EXISTS opportunity_signals (
    id TEXT PRIMARY KEY, ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
    signal_type TEXT NOT NULL, description TEXT NOT NULL,
    conviction_score INTEGER NOT NULL, ingested_at TEXT NOT NULL,
    UNIQUE(ticker, computed_date, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON opportunity_signals(ticker);
CREATE VIEW IF NOT EXISTS thesis_latest AS
SELECT * FROM thesis_versions
WHERE (ticker, version_num) IN (
    SELECT ticker, MAX(version_num) FROM thesis_versions GROUP BY ticker
);
"""


def make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with full Phase 4 schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_FULL_SCHEMA)
    return conn


def _make_thesis(fair_value_brl: float = 48.30) -> "InvestmentThesis":
    """Build a minimal valid InvestmentThesis for use in tests."""
    from src.intelligence_layer import Driver, InvestmentThesis, Risk

    return InvestmentThesis(
        bull_case="Upside significativo com expansao de margens e crescimento de receita.",
        bear_case="Risco de desaceleracao macro com Selic elevada comprimindo multiplos.",
        drivers=[
            Driver(title="Crescimento de Receita", description="Expansao para novos mercados", impact="HIGH"),
            Driver(title="Eficiencia Operacional", description="Reducao de custos em andamento", impact="MEDIUM"),
            Driver(title="Dividendos", description="Politica de dividendos generosa", impact="LOW"),
        ],
        risks=[
            Risk(title="Macro", description="Alta da Selic impacta custo de capital", severity="HIGH"),
            Risk(title="Cambio", description="Exposicao a dolar em 30% da receita", severity="MEDIUM"),
            Risk(title="Regulatorio", description="Mudancas regulatorias no setor", severity="LOW"),
        ],
        fair_value_brl=fair_value_brl,
        methodology_disclosure="DCF FCFF com WACC 12.5% e crescimento terminal 3.5%",
        positioning="COMPRAR",
        confidence="ALTA",
        rationale="Upside de 20% com fundamentos solidos e dividendos crescentes.",
        summary_one_line="PETR4 com upside de 20% — COMPRAR com confianca ALTA.",
    )


# -- INT-01: Schema validation ------------------------------------------------


def test_investment_thesis_schema():
    """INT-01: InvestmentThesis Pydantic schema validates correct structure with Driver/Risk sub-objects."""
    from src.intelligence_layer import Driver, InvestmentThesis, Risk

    thesis = _make_thesis()
    assert thesis.positioning == "COMPRAR"
    assert thesis.confidence == "ALTA"
    assert len(thesis.drivers) == 3
    assert len(thesis.risks) == 3
    assert all(isinstance(d, Driver) for d in thesis.drivers)
    assert all(isinstance(r, Risk) for r in thesis.risks)
    assert thesis.fair_value_brl == 48.30
    assert thesis.summary_one_line != ""


def test_driver_impact_literals():
    """INT-01: Driver.impact must be HIGH/MEDIUM/LOW — Pydantic rejects other values."""
    from pydantic import ValidationError

    from src.intelligence_layer import Driver

    with pytest.raises(ValidationError):
        Driver(title="Test", description="Test", impact="VERY_HIGH")


def test_risk_severity_literals():
    """INT-01: Risk.severity must be HIGH/MEDIUM/LOW — Pydantic rejects other values."""
    from pydantic import ValidationError

    from src.intelligence_layer import Risk

    with pytest.raises(ValidationError):
        Risk(title="Test", description="Test", severity="CRITICAL")


def test_generate_thesis_returns_valid_schema(monkeypatch):
    """INT-01: IntelligenceClient.generate_thesis() returns InvestmentThesis with all required fields."""
    from src.intelligence_layer import IntelligenceClient

    mock_thesis = _make_thesis()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_thesis
    # instructor 1.15.1 uses from_provider (not from_anthropic — API changed in >=1.0 refactor)
    monkeypatch.setattr("instructor.from_provider", lambda *a, **k: mock_client)
    client = IntelligenceClient()
    result = client.generate_thesis("PETR4", "prompt text", "system text")
    assert isinstance(result, type(mock_thesis))
    assert result.positioning in ("COMPRAR", "MANTER", "VENDER")
    assert result.fair_value_brl == 48.30


def test_hard_fail_on_validation_error(monkeypatch):
    """INT-01 + D-05: IngestionError raised on instructor validation exhaustion; no partial thesis stored."""
    from src.intelligence_layer import IntelligenceClient
    from src.utils.errors import IngestionError

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("InstructorRetryException: max retries exceeded")
    # instructor 1.15.1 uses from_provider (not from_anthropic — API changed in >=1.0 refactor)
    monkeypatch.setattr("instructor.from_provider", lambda *a, **k: mock_client)
    client = IntelligenceClient()
    with pytest.raises(IngestionError):
        client.generate_thesis("PETR4", "prompt", "system")


# -- INT-02: DCF cross-check --------------------------------------------------


def test_dcf_deviation_flag():
    """INT-02: dcf_deviation_flag=True when thesis.fair_value_brl deviates >10% from DCF."""
    from src.intelligence_layer import _check_dcf_deviation

    thesis = _make_thesis(fair_value_brl=55.00)  # 55 vs DCF 48 = 14.6% deviation
    flag = _check_dcf_deviation(thesis, dcf_fair_value=48.30)
    assert flag is True


def test_dcf_deviation_within_tolerance():
    """INT-02: dcf_deviation_flag=False when deviation is within +-10%."""
    from src.intelligence_layer import _check_dcf_deviation

    thesis = _make_thesis(fair_value_brl=50.00)  # 50 vs DCF 48.30 = 3.5% deviation
    flag = _check_dcf_deviation(thesis, dcf_fair_value=48.30)
    assert flag is False


# -- INT-03: Hash gate + daily cap --------------------------------------------


def test_compute_input_hash_deterministic():
    """INT-03: Same inputs always produce the same hash (deterministic)."""
    from src.intelligence_layer import compute_input_hash

    multiples = {"pe_ratio": 10.5, "ev_ebitda": 6.2, "pb_ratio": 1.8, "dividend_yield": 0.06, "ev_revenue": 1.2}
    h1 = compute_input_hash(48.30, 0.20, multiples, 0.1065, 0.0215, 62, ["https://a.com", "https://b.com"])
    h2 = compute_input_hash(48.30, 0.20, multiples, 0.1065, 0.0215, 62, ["https://b.com", "https://a.com"])
    assert h1 == h2  # sorted(news_urls) makes it order-independent


@pytest.mark.xfail(reason="run_ticker not yet implemented — Plan 04-02")
def test_hash_gate_skips_on_match(monkeypatch):
    """INT-03: run_ticker() skips generation when same input_hash already exists in thesis_versions."""
    conn = make_db()
    existing_hash = "aabbccdd" * 8  # 64-char fake hash
    conn.execute(
        "INSERT INTO thesis_versions (id, ticker, version_num, generated_at, input_hash, "
        "positioning, confidence, fair_value_brl, thesis_json) VALUES (?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", 1, datetime.now(timezone.utc).isoformat(),
         existing_hash, "COMPRAR", "ALTA", 48.30, "{}"),
    )
    conn.commit()
    monkeypatch.setattr("src.intelligence_layer.compute_input_hash", lambda *a, **k: existing_hash)
    monkeypatch.setattr("src.intelligence_layer.get_connection", lambda: conn)
    from src.intelligence_layer import run_ticker

    result = run_ticker("PETR4")
    assert result.skipped is True
    assert result.skip_reason == "hash_match"
    conn.close()


@pytest.mark.xfail(reason="run_ticker not yet implemented — Plan 04-02")
def test_daily_cap_after_two_runs(monkeypatch):
    """INT-03 + D-11: run_ticker() skips after 2 thesis rows for same ticker today."""
    conn = make_db()
    today = date.today().isoformat()
    for i in range(2):
        conn.execute(
            "INSERT INTO thesis_versions (id, ticker, version_num, generated_at, input_hash, "
            "positioning, confidence, fair_value_brl, thesis_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "PETR4", i + 1, f"{today}T10:0{i}:00+00:00",
             f"hash{i}", "MANTER", "MEDIA", 45.00, "{}"),
        )
    conn.commit()
    monkeypatch.setattr("src.intelligence_layer.get_connection", lambda: conn)
    from src.intelligence_layer import run_ticker

    result = run_ticker("PETR4")
    assert result.skipped is True
    assert result.skip_reason == "daily_cap"
    conn.close()


# -- INT-04: Thesis versioning ------------------------------------------------


@pytest.mark.xfail(reason="run_ticker not yet implemented — Plan 04-02")
def test_thesis_versions_write(monkeypatch):
    """INT-04: thesis_versions row written with correct version_num, input_hash, positioning, thesis_json."""
    conn = make_db()
    mock_thesis = _make_thesis()
    monkeypatch.setattr("src.intelligence_layer.get_connection", lambda: conn)
    monkeypatch.setattr("src.intelligence_layer.compute_input_hash", lambda *a, **k: "testhash123")
    mock_client_instance = MagicMock()
    mock_client_instance.generate_thesis.return_value = mock_thesis
    monkeypatch.setattr("src.intelligence_layer.IntelligenceClient", lambda: mock_client_instance)
    from src.intelligence_layer import run_ticker

    result = run_ticker("PETR4")
    assert result.skipped is False
    assert result.thesis is not None
    row = conn.execute(
        "SELECT * FROM thesis_versions WHERE ticker = ?", ("PETR4",)
    ).fetchone()
    assert row is not None
    assert row["version_num"] == 1
    assert row["positioning"] == "COMPRAR"
    assert row["input_hash"] == "testhash123"
    assert json.loads(row["thesis_json"])["positioning"] == "COMPRAR"
    conn.close()


@pytest.mark.xfail(reason="thesis_latest VIEW tested in test_db_schema.py::test_thesis_latest_view — this tests query behaviour")
def test_thesis_latest_view_query(monkeypatch):
    """INT-04: thesis_latest VIEW returns only MAX(version_num) row per ticker."""
    conn = make_db()
    for v in (1, 2, 3):
        conn.execute(
            "INSERT INTO thesis_versions (id, ticker, version_num, generated_at, input_hash, "
            "positioning, confidence, fair_value_brl, thesis_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "PETR4", v, datetime.now(timezone.utc).isoformat(),
             f"hash{v}", "COMPRAR" if v == 3 else "MANTER", "ALTA", 48.30 + v, "{}"),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM thesis_latest WHERE ticker = ?", ("PETR4",)).fetchone()
    assert row is not None
    assert row["version_num"] == 3
    conn.close()


# -- INT-05: Opportunity signals ----------------------------------------------


@pytest.mark.xfail(reason="compute_opportunity_signals not yet implemented — Plan 04-03")
def test_dcf_divergence_signal():
    """INT-05: DCF_DIVERGENCE signal emitted when price vs DCF fair value divergence > 20%."""
    from src.intelligence_layer import _score_dcf_divergence

    # 40 price vs 55 fair_value -> 37.5% divergence -> score > 0
    score = _score_dcf_divergence(price=40.0, fair_value=55.0)
    assert score > 0
    assert score <= 40


@pytest.mark.xfail(reason="_score_dcf_divergence not yet implemented — Plan 04-03")
def test_dcf_divergence_below_threshold():
    """INT-05: DCF_DIVERGENCE signal NOT emitted when divergence <= 20%."""
    from src.intelligence_layer import _score_dcf_divergence

    score = _score_dcf_divergence(price=48.0, fair_value=50.0)  # 4.2% divergence
    assert score == 0


@pytest.mark.xfail(reason="compute_opportunity_signals not yet implemented — Plan 04-03")
def test_momentum_crossover_signal():
    """INT-05: MOMENTUM_CROSSOVER signal emitted when golden_cross=1 and momentum_score>=60."""
    from src.intelligence_layer import compute_opportunity_signals

    conn = make_db()
    today = date.today().isoformat()
    # Insert financial_signals with golden_cross + high momentum
    conn.execute(
        "INSERT INTO financial_signals (id,ticker,computed_date,rsi_14,macd_line,macd_signal,"
        "macd_histogram,ma_50,ma_200,golden_cross,death_cross,momentum_score,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", today, 65.0, 0.5, 0.3, 0.2, 42.0, 38.0, 1, 0, 72,
         datetime.now(timezone.utc).isoformat()),
    )
    # Insert financial_dcf so DCF_DIVERGENCE can be computed (price ~= fair_value — no divergence signal)
    conn.execute(
        "INSERT INTO financial_multiples (id,ticker,computed_date,price,market_cap,pe_ratio,"
        "ev_ebitda,pb_ratio,dividend_yield,ev_revenue,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", today, 40.0, 1e10, 10.0, 6.0, 1.5, 0.06, 1.2,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "INSERT INTO financial_dcf (id,ticker,computed_date,valuation_method,fair_value_brl,"
        "upside_pct,wacc,terminal_growth,selic_used,cds_used,used_fallback,confidence_flag,ingested_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", today, "DCF_FCFF", 41.0, 0.025, 0.125, 0.035,
         0.1065, 0.0215, 0, None, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    signals = compute_opportunity_signals("PETR4", conn)
    momentum_signals = [s for s in signals if s.signal_type == "MOMENTUM_CROSSOVER"]
    assert len(momentum_signals) >= 1
    assert momentum_signals[0].conviction_score >= 40
    conn.close()


@pytest.mark.xfail(reason="compute_opportunity_signals not yet implemented — Plan 04-03")
def test_ipe_event_signal():
    """INT-05: IPE_EVENT signal emitted when IPE event in last 30 days (no normalized_name filter)."""
    from src.intelligence_layer import compute_opportunity_signals

    conn = make_db()
    today = date.today().isoformat()
    # Insert IPE event with NULL normalized_name — Pitfall 7 guard
    conn.execute(
        "INSERT INTO cvm_statements (id,ticker,cvm_code,year,period_type,account_code,"
        "account_name,normalized_name,value,reference_date,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", "9512", 2026, "IPE", None, "Fato Relevante", None,
         None, today, datetime.now(timezone.utc).isoformat()),
    )
    # Insert financial_multiples + dcf for the signal computation to proceed
    conn.execute(
        "INSERT INTO financial_multiples (id,ticker,computed_date,price,market_cap,pe_ratio,"
        "ev_ebitda,pb_ratio,dividend_yield,ev_revenue,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", today, 40.0, 1e10, 10.0, 6.0, 1.5, 0.06, 1.2,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "INSERT INTO financial_dcf (id,ticker,computed_date,valuation_method,fair_value_brl,"
        "upside_pct,wacc,terminal_growth,selic_used,cds_used,used_fallback,confidence_flag,ingested_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", today, "DCF_FCFF", 41.0, 0.025, 0.125, 0.035,
         0.1065, 0.0215, 0, None, datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "INSERT INTO financial_signals (id,ticker,computed_date,rsi_14,macd_line,macd_signal,"
        "macd_histogram,ma_50,ma_200,golden_cross,death_cross,momentum_score,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "PETR4", today, 50.0, 0.1, 0.1, 0.0, 40.0, 38.0, 0, 0, 50,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    signals = compute_opportunity_signals("PETR4", conn)
    ipe_signals = [s for s in signals if s.signal_type == "IPE_EVENT"]
    assert len(ipe_signals) == 1
    assert ipe_signals[0].conviction_score == 30
    conn.close()


@pytest.mark.xfail(reason="_score_dcf_divergence not yet implemented — Plan 04-03")
def test_signal_conviction_threshold():
    """INT-05: Signals with conviction_score < 40 are filtered out from compute_opportunity_signals()."""
    from src.intelligence_layer import _score_dcf_divergence

    # 10% divergence -> below 20% threshold -> score 0 -> filtered out
    score = _score_dcf_divergence(price=50.0, fair_value=55.0)
    assert score == 0  # 10% divergence is below 20% threshold


# -- INT-06: opportunity_signals table ----------------------------------------


@pytest.mark.xfail(reason="_write_opportunity_signals not yet implemented — Plan 04-03")
def test_opportunity_signals_write(monkeypatch):
    """INT-06: opportunity_signals table receives top-3 signals via INSERT OR REPLACE."""
    from src.intelligence_layer import OpportunitySignal, _write_opportunity_signals

    conn = make_db()
    today = date.today().isoformat()
    signals = [
        OpportunitySignal(ticker="PETR4", signal_type="DCF_DIVERGENCE",
                          description="Upside 35%", conviction_score=35,
                          generated_at=datetime.now(timezone.utc).isoformat()),
        OpportunitySignal(ticker="PETR4", signal_type="MOMENTUM_CROSSOVER",
                          description="Golden cross", conviction_score=25,
                          generated_at=datetime.now(timezone.utc).isoformat()),
        OpportunitySignal(ticker="PETR4", signal_type="IPE_EVENT",
                          description="Fato relevante ontem", conviction_score=30,
                          generated_at=datetime.now(timezone.utc).isoformat()),
    ]
    _write_opportunity_signals("PETR4", signals, conn)
    conn.commit()
    rows = conn.execute(
        "SELECT * FROM opportunity_signals WHERE ticker = ? ORDER BY conviction_score DESC",
        ("PETR4",),
    ).fetchall()
    assert len(rows) == 3
    # INSERT OR REPLACE — second call with same (ticker, computed_date, signal_type) must not duplicate
    _write_opportunity_signals("PETR4", signals, conn)
    conn.commit()
    rows2 = conn.execute(
        "SELECT COUNT(*) FROM opportunity_signals WHERE ticker = ?", ("PETR4",)
    ).fetchone()[0]
    assert rows2 == 3  # no duplicates
    conn.close()
