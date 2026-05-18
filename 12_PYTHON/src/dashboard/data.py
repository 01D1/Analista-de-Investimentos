"""
data.py
-------
Dashboard query layer for Phase 5 Delivery.

Fluxo: ingestion.db -> cached query functions -> Streamlit pages
Uso:
    from src.dashboard.data import get_watchlist_summary, get_asset_detail
"""
from __future__ import annotations

import json

import streamlit as st

from src.ingestion.db import DB_PATH, get_connection
from src.utils.logger import get_logger

log = get_logger(__name__)


@st.cache_data(ttl=300)
def get_watchlist_summary() -> list[dict]:
    """Retorna lista de tickers com resumo de tese, multiples e DCF, ordenado por upside DESC.

    Cada dict contem: ticker, positioning, confidence, fair_value_brl, generated_at,
    price, pe_ratio, ev_ebitda, upside_pct.
    """
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT
                tl.ticker,
                tl.positioning,
                tl.confidence,
                tl.fair_value_brl,
                tl.generated_at,
                fm.price,
                fm.pe_ratio,
                fm.ev_ebitda,
                fd.upside_pct
            FROM thesis_latest tl
            LEFT JOIN financial_multiples fm
                ON fm.ticker = tl.ticker
               AND fm.computed_date = (
                   SELECT MAX(computed_date)
                   FROM financial_multiples
                   WHERE ticker = tl.ticker
               )
            LEFT JOIN financial_dcf fd
                ON fd.ticker = tl.ticker
               AND fd.computed_date = (
                   SELECT MAX(computed_date)
                   FROM financial_dcf
                   WHERE ticker = tl.ticker
               )
            ORDER BY fd.upside_pct DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()  # WR-06: sempre fechar mesmo em excecao


@st.cache_data(ttl=300)
def get_asset_detail(ticker: str) -> dict | None:
    """Retorna detalhes completos de um ativo (tese, DCF, LTM, multiples, noticias, macro).

    Retorna None se o ticker nao estiver em thesis_latest.
    thesis_json e deserializado via json.loads() antes de retornar.
    """
    # WR-04: call get_macro_panel() before opening conn to avoid nested open connections
    macro = get_macro_panel()
    conn = get_connection(DB_PATH)
    try:
        thesis_row = conn.execute(
            "SELECT * FROM thesis_latest WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not thesis_row:
            return None
        result = dict(thesis_row)
        # T-05-01 / Pitfall 5: sempre deserializar thesis_json — e TEXT no DB
        result["thesis"] = json.loads(result["thesis_json"])

        dcf_row = conn.execute(
            "SELECT * FROM financial_dcf WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        result["dcf"] = dict(dcf_row) if dcf_row else {}

        ltm_row = conn.execute(
            "SELECT * FROM financial_ltm WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        result["ltm"] = dict(ltm_row) if ltm_row else {}

        multiples_row = conn.execute(
            "SELECT * FROM financial_multiples WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        result["multiples"] = dict(multiples_row) if multiples_row else {}

        news_rows = conn.execute(
            "SELECT * FROM news_articles WHERE ticker_tags LIKE ? ORDER BY published_at DESC LIMIT 5",
            (f'%"{ticker}"%',),
        ).fetchall()
        result["news"] = [dict(r) for r in news_rows]

        result["macro"] = macro
        return result
    finally:
        conn.close()  # WR-06: sempre fechar mesmo em excecao


@st.cache_data(ttl=300)
def get_macro_panel() -> dict[str, list[dict]]:
    """Retorna series macro do BCB com historico de 365 dias, ordenado cronologicamente.

    Chaves: selic, ipca_12m, ptax, cds_brasil, pib_nominal.
    Cada valor e lista de {date, value} dicts em ordem crescente de data.
    """
    SERIES = {
        "selic": 11,
        "ipca_12m": 433,
        "ptax": 1,
        "cds_brasil": 29039,
        "pib_nominal": 4380,
    }
    conn = get_connection(DB_PATH)
    try:
        result: dict[str, list[dict]] = {}
        for name, code in SERIES.items():
            rows = conn.execute(
                "SELECT date, value FROM macro_series"
                " WHERE series_code = ?"
                " ORDER BY date DESC LIMIT 365",
                (code,),
            ).fetchall()
            # Reverter para ordem cronologica crescente
            result[name] = [dict(r) for r in reversed(rows)]
        return result
    finally:
        conn.close()  # WR-06: sempre fechar mesmo em excecao


@st.cache_data(ttl=300)
def get_opportunities() -> list[dict]:
    """Retorna top 10 sinais de oportunidade do dia, ordenados por conviction_score DESC."""
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT ticker, signal_type, description, conviction_score, computed_date
            FROM opportunity_signals
            WHERE computed_date = (SELECT MAX(computed_date) FROM opportunity_signals)
            ORDER BY conviction_score DESC
            LIMIT 10
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()  # WR-06: sempre fechar mesmo em excecao
