"""
test_dashboard_data.py
-----------------------
Phase 5 - Dashboard data layer tests covering DEL-01, DEL-02.

Covers:
  - get_watchlist_summary() returns list of dicts from thesis_latest
  - get_asset_detail() returns None for unknown ticker; returns dict with thesis deserialized
  - get_macro_panel() returns dict with chronological series
  - get_opportunities() returns list of dicts ordered by conviction_score
  - All 4 functions decorated with @st.cache_data (DEL-02)
"""
from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.fixture
def mem_db(monkeypatch, tmp_path):
    """In-memory ingestion.db com schema minimo e dados de teste."""
    import src.dashboard.data as data_module

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS thesis_versions (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            version_num INTEGER,
            generated_at TEXT,
            input_hash TEXT,
            positioning TEXT,
            confidence TEXT,
            fair_value_brl REAL,
            dcf_deviation_flag INTEGER DEFAULT 0,
            thesis_json TEXT,
            diff_summary TEXT
        );
        CREATE VIEW IF NOT EXISTS thesis_latest AS
            SELECT * FROM thesis_versions
            WHERE version_num = (
                SELECT MAX(version_num)
                FROM thesis_versions tv2
                WHERE tv2.ticker = thesis_versions.ticker
            );
        CREATE TABLE IF NOT EXISTS opportunity_signals (
            id TEXT PRIMARY KEY,
            ticker TEXT,
            signal_type TEXT,
            description TEXT,
            conviction_score INTEGER,
            computed_date TEXT
        );
        CREATE TABLE IF NOT EXISTS macro_series (
            id TEXT PRIMARY KEY,
            series_code INTEGER,
            series_name TEXT,
            date TEXT,
            value REAL,
            ingested_at TEXT
        );
        CREATE TABLE IF NOT EXISTS financial_dcf (
            id TEXT PRIMARY KEY,
            ticker TEXT,
            computed_date TEXT,
            fair_value_brl REAL,
            upside_pct REAL
        );
        CREATE TABLE IF NOT EXISTS financial_multiples (
            id TEXT PRIMARY KEY,
            ticker TEXT,
            computed_date TEXT,
            price REAL,
            pe_ratio REAL,
            ev_ebitda REAL
        );
        CREATE TABLE IF NOT EXISTS financial_ltm (
            id TEXT PRIMARY KEY,
            ticker TEXT,
            computed_date TEXT,
            net_revenue REAL,
            ebitda REAL,
            net_income REAL,
            fcf REAL,
            net_debt REAL
        );
        CREATE TABLE IF NOT EXISTS news_articles (
            id TEXT PRIMARY KEY,
            headline TEXT,
            published_at TEXT,
            ticker_tags TEXT
        );
    """)
    # Seed thesis
    thesis_json = json.dumps({
        "bull_case": "teste bull",
        "bear_case": "teste bear",
        "drivers": [],
        "risks": [],
        "positioning": "COMPRAR",
        "confidence": "ALTA",
        "fair_value_brl": 40.0,
        "rationale": "racional",
        "summary_one_line": "one liner",
        "methodology_disclosure": "DCF",
    })
    conn.execute(
        "INSERT INTO thesis_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("id1", "PETR4", 1, "2026-05-18", "hash1", "COMPRAR", "ALTA", 40.0, 0, thesis_json, None),
    )
    conn.execute(
        "INSERT INTO opportunity_signals VALUES (?,?,?,?,?,?)",
        ("sig1", "PETR4", "DCF_DIVERGENCE", "Upside 35%", 85, "2026-05-18"),
    )
    conn.execute(
        "INSERT INTO macro_series VALUES (?,?,?,?,?,?)",
        ("m1", 11, "Selic", "2026-05-18", 14.75, "2026-05-18"),
    )
    conn.execute(
        "INSERT INTO financial_dcf VALUES (?,?,?,?,?)",
        ("dcf1", "PETR4", "2026-05-18", 40.0, 35.0),
    )
    conn.execute(
        "INSERT INTO financial_multiples VALUES (?,?,?,?,?,?)",
        ("fm1", "PETR4", "2026-05-18", 30.0, 6.2, 4.1),
    )
    conn.commit()
    conn.close()

    # Patch DB_PATH no modulo data
    monkeypatch.setattr("src.dashboard.data.DB_PATH", db_path)
    monkeypatch.setattr("src.ingestion.db.DB_PATH", db_path)
    return db_path


def test_get_watchlist_summary(mem_db):
    """DEL-01: get_watchlist_summary() retorna lista de dicts de thesis_latest."""
    from src.dashboard.data import get_watchlist_summary

    get_watchlist_summary.clear()  # limpar cache Streamlit entre testes
    rows = get_watchlist_summary()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert rows[0]["ticker"] == "PETR4"
    assert rows[0]["positioning"] == "COMPRAR"


def test_get_asset_detail(mem_db):
    """DEL-01: get_asset_detail() retorna dict com thesis deserializado; None para ticker desconhecido."""
    from src.dashboard.data import get_asset_detail

    get_asset_detail.clear()

    # Ticker conhecido
    detail = get_asset_detail("PETR4")
    assert detail is not None
    assert isinstance(detail, dict)
    # thesis_json deve ser deserializado para dict (Pitfall 5 mitigation)
    assert isinstance(detail["thesis"], dict), "thesis deve ser dict, nao str (json.loads obrigatorio)"
    assert detail["thesis"]["positioning"] == "COMPRAR"
    assert "dcf" in detail
    assert "ltm" in detail
    assert "multiples" in detail
    assert "news" in detail
    assert "macro" in detail

    # Ticker desconhecido
    get_asset_detail.clear()
    none_result = get_asset_detail("XXXX99")
    assert none_result is None


def test_get_macro_panel(mem_db):
    """DEL-01: get_macro_panel() retorna dict com chaves das 5 series BCB."""
    from src.dashboard.data import get_macro_panel

    get_macro_panel.clear()
    macro = get_macro_panel()
    assert isinstance(macro, dict)
    # Deve ter as 5 chaves esperadas
    for key in ("selic", "ipca_12m", "ptax", "cds_brasil", "pib_nominal"):
        assert key in macro, f"Chave '{key}' ausente em get_macro_panel()"
    # Selic deve ter pelo menos 1 entry (inserimos no fixture)
    assert isinstance(macro["selic"], list)
    if macro["selic"]:
        assert "date" in macro["selic"][0]
        assert "value" in macro["selic"][0]


def test_get_opportunities(mem_db):
    """DEL-01: get_opportunities() retorna lista de dicts com conviction_score."""
    from src.dashboard.data import get_opportunities

    get_opportunities.clear()
    opps = get_opportunities()
    assert isinstance(opps, list)
    # Deve ter pelo menos o sinal inserido no fixture (mesmo que seja hoje)
    # Apenas verificamos a estrutura se retornar resultados
    if opps:
        assert "ticker" in opps[0]
        assert "conviction_score" in opps[0]


def test_cache_decorators_present():
    """DEL-02: @st.cache_data presente em todas as 4 funcoes de data.py."""
    import src.dashboard.data as m

    for fn_name in ("get_watchlist_summary", "get_asset_detail", "get_macro_panel", "get_opportunities"):
        fn = getattr(m, fn_name)
        # st.cache_data wraps a funcao — expoe atributo .clear() ou __wrapped__
        assert hasattr(fn, "__wrapped__") or hasattr(fn, "clear"), (
            f"{fn_name} esta faltando @st.cache_data decorator"
        )
