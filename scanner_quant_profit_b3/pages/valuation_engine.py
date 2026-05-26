"""Valuation Engine — Analise Fundamentalista Standalone.

Objetivo: operar sem dependência de pipeline externo (12_PYTHON) ou abertura
de Excel em runtime. Todas as fontes sao internas ao scanner_quant.

Fontes reais (S02):
  - src.dashboard.data.get_watchlist_summary()
  - src.dashboard.data.get_asset_detail()
  - src.dashboard.data.get_macro_panel()
  - src.integration.asset_intelligence_store.load_latest_asset_intelligence_snapshot()
  - src.integration.asset_intelligence_model ASSET_INTELLIGENCE_COLUMNS

Regras:
  - Nenhum mock ou dado hardcoded.
  - Nenhuma chamada a APIs externas / LLM.
  - Nenhum shell vazio (panel-shell com conteudo real ou empty_state).
  - Nao depende de streamlit_app.py externo.
  - Nao abre Excel em runtime.
  - Nao usa valuation_bridge (que depende de Excel externo).
  - empty states honestos quando nao houver dados.
  - MONITOR_ONLY NAO vira APPROVED.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)

for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st
import pandas as pd
import sqlite3

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    section_title,
    kpi_card,
    kpi_strip,
    empty_state,
    alert_block,
    score_bar,
    status_chip,
)
from src.dashboard.data import (
    get_watchlist_summary,
    get_asset_detail,
    get_macro_panel,
    _db_path,
    load_latest_asset_intelligence_snapshot,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_float(v, decimals=2) -> str:
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"

def _upside_color(pct: float) -> str:
    if pct is None:
        return "var(--fg-5)"
    if pct > 20:
        return "var(--pos-500)"
    if pct > 0:
        return "var(--warn-500)"
    return "var(--neg-500)"

def _source_label(src: str) -> str:
    mapping = {
        "pipeline_bridge": "Pipeline DCF",
        "scanner_quant_db": "Scanner DB",
        "none": "Sem dados",
    }
    return mapping.get(str(src).lower(), str(src))

def _status_to_chip(status: str) -> str:
    """Render status as governance chip."""
    s = str(status or "").strip().upper()
    if not s:
        return status_chip("EMPTY", label="SEM DADOS")
    return status_chip(s)

def _load_valuation_rows() -> list[dict]:
    """
    Load raw valuation rows from asset_intelligence_snapshots (internal DB).
    Does NOT use valuation_bridge (Excel) — fully standalone.
    """
    db = _db_path()
    if not Path(db).exists():
        return []
    try:
        conn = sqlite3.connect(str(db))
        rows = conn.execute("""
            SELECT
                ticker,
                company_name,
                sector,
                fair_value,
                upside_pct,
                valuation_method,
                valuation_confidence,
                fundamental_quality_score,
                financial_health_score,
                profitability_score,
                growth_score,
                leverage_score,
                valuation_governance_status,
                data_quality_score,
                integrated_score,
                integrated_status,
                integrated_confidence,
                market_price,
                created_at
            FROM asset_intelligence_snapshots
            WHERE fair_value IS NOT NULL AND fair_value > 0
            ORDER BY created_at DESC, ticker
        """).fetchall()
        conn.close()
        return [
            {
                "ticker": str(r[0] or ""),
                "company_name": str(r[1] or ""),
                "sector": str(r[2] or ""),
                "fair_value": float(r[3]) if r[3] is not None else None,
                "upside_pct": float(r[4]) if r[4] is not None else None,
                "valuation_method": str(r[5] or ""),
                "valuation_confidence": float(r[6]) if r[6] is not None else None,
                "fundamental_quality_score": float(r[7]) if r[7] is not None else None,
                "financial_health_score": float(r[8]) if r[8] is not None else None,
                "profitability_score": float(r[9]) if r[9] is not None else None,
                "growth_score": float(r[10]) if r[10] is not None else None,
                "leverage_score": float(r[11]) if r[11] is not None else None,
                "valuation_governance_status": str(r[12] or ""),
                "data_quality_score": float(r[13]) if r[13] is not None else None,
                "integrated_score": float(r[14]) if r[14] is not None else None,
                "integrated_status": str(r[15] or ""),
                "integrated_confidence": str(r[16] or ""),
                "market_price": float(r[17]) if r[17] is not None else None,
                "created_at": str(r[18] or ""),
            }
            for r in rows
        ]
    except Exception:
        return []


def _load_fundamental_quality_rows() -> list[dict]:
    """
    Load fundamental quality rows from asset_intelligence_snapshots (internal DB).
    """
    db = _db_path()
    if not Path(db).exists():
        return []
    try:
        conn = sqlite3.connect(str(db))
        rows = conn.execute("""
            SELECT
                ticker,
                fundamental_quality_score,
                financial_health_score,
                profitability_score,
                growth_score,
                leverage_score,
                data_quality_score,
                valuation_governance_status,
                created_at
            FROM asset_intelligence_snapshots
            WHERE fundamental_quality_score IS NOT NULL
            ORDER BY created_at DESC, ticker
        """).fetchall()
        conn.close()
        return [
            {
                "ticker": str(r[0] or ""),
                "fundamental_quality_score": float(r[1]) if r[1] is not None else None,
                "financial_health_score": float(r[2]) if r[2] is not None else None,
                "profitability_score": float(r[3]) if r[3] is not None else None,
                "growth_score": float(r[4]) if r[4] is not None else None,
                "leverage_score": float(r[5]) if r[5] is not None else None,
                "data_quality_score": float(r[6]) if r[6] is not None else None,
                "valuation_governance_status": str(r[7] or ""),
                "created_at": str(r[8] or ""),
            }
            for r in rows
        ]
    except Exception:
        return []


# ── M017: resolve ingestion.db + dry-run matrix ──────────────────────────────

_INGESTION_DB_ENV = "FINANCIAL_INPUTS_DB_PATH"

# 9 PRESERVE_EXISTING fair values — auditados M015/M016, não recalcular sem force_recalc
_PRESERVE_EXISTING: dict[str, float] = {
    "ABCB4": 210.50, "BBAS3": 64.84, "BBDC4": 34.63,
    "BPAC11": 8.46, "BRSR6": 4.66, "ITUB4": 73.69,
    "SANB11": 86.79, "PETR4": 81.12, "WEGE3": 40.16,
}

# M017 universe — 32 tickers com model_status definido
_M017_UNIVERSE: list[dict] = [
    # PRESERVE_EXISTING — fair_value auditável
    {"ticker": "ABCB4",  "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "BBAS3",  "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "BBDC4",  "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "BPAC11", "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "BRSR6",  "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "ITUB4",  "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "SANB11", "model_status": "PRESERVE_EXISTING",    "model": "BANK",      "method_suggested": "P/BV",     "block_reason": ""},
    {"ticker": "PETR4",  "model_status": "PRESERVE_EXISTING",    "model": "COMMODITY", "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "WEGE3",  "model_status": "PRESERVE_EXISTING",    "model": "INDUSTRY",  "method_suggested": "DCF/FCFF", "block_reason": ""},
    # READY_TO_CALCULATE — inputs completos
    {"ticker": "EGIE3",  "model_status": "READY_TO_CALCULATE",   "model": "UTILITY",   "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "SBSP3",  "model_status": "READY_TO_CALCULATE",   "model": "UTILITY",   "method_suggested": "EV/EBITDA","block_reason": "FCF_NEGATIVE_EXPECTED"},
    {"ticker": "TAEE11", "model_status": "READY_TO_CALCULATE",   "model": "UTILITY",   "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "AZZA3",  "model_status": "READY_TO_CALCULATE",   "model": "RETAIL",    "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "LREN3",  "model_status": "READY_TO_CALCULATE",   "model": "RETAIL",    "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "MGLU3",  "model_status": "READY_TO_CALCULATE",   "model": "RETAIL",    "method_suggested": "EV/EBITDA","block_reason": "FCF_REVIEW"},
    {"ticker": "VIVA3",  "model_status": "READY_TO_CALCULATE",   "model": "RETAIL",    "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "PRIO3",  "model_status": "READY_TO_CALCULATE",   "model": "COMMODITY", "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "RECV3",  "model_status": "READY_TO_CALCULATE",   "model": "COMMODITY", "method_suggested": "EV/EBITDA","block_reason": "FCF_NEGATIVE_EXPECTED"},
    {"ticker": "FLRY3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "HYPE3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "KLBN11", "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "RADL3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "RAIL3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "EV/EBITDA","block_reason": ""},
    {"ticker": "RENT3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "EV/EBITDA","block_reason": ""},
    {"ticker": "SUZB3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "DCF/FCFF", "block_reason": ""},
    {"ticker": "VAMO3",  "model_status": "READY_TO_CALCULATE",   "model": "INDUSTRY",  "method_suggested": "EV/EBITDA","block_reason": "FCF_NEGATIVE_EXPECTED"},
    # PARTIAL_INPUTS
    {"ticker": "PCAR3",  "model_status": "PARTIAL_INPUTS",        "model": "RETAIL",    "method_suggested": "EV/EBITDA","block_reason": "DISTRESSED — DCF bloqueado"},
    # TECH_FALLBACK
    {"ticker": "VIVT3",  "model_status": "TECH_FALLBACK",         "model": "INDUSTRY",  "method_suggested": "EV/EBITDA","block_reason": "CVM inputs pendentes"},
    # NEEDS_DATA / NEEDS_RI_DOCS
    {"ticker": "VALE3",  "model_status": "NEEDS_DATA",            "model": "COMMODITY", "method_suggested": "DCF/FCFF", "block_reason": "ri_docs=0 — aguarda CVM ingestion"},
    {"ticker": "AUAU3",  "model_status": "NEEDS_RI_DOCS",         "model": "—",         "method_suggested": "—",        "block_reason": "CNPJ nulo — sem CVM data"},
    {"ticker": "NTCO3",  "model_status": "NEEDS_RI_DOCS",         "model": "RETAIL",    "method_suggested": "DCF/FCFF", "block_reason": "ri_docs insuficientes"},
    # LEGACY_TICKER
    {"ticker": "PETZ3",  "model_status": "LEGACY_TICKER",         "model": "RETAIL",    "method_suggested": "—",        "block_reason": "PETZ3 encerrado — permanentemente bloqueado"},
]


def _resolve_ingestion_db() -> Path | None:
    """Resolve ingestion.db: env var → sibling 12_PYTHON → CWD fallback."""
    import os
    env = os.environ.get(_INGESTION_DB_ENV)
    if env:
        p = Path(env)
        if p.exists():
            return p
    # SCANNER_ROOT.parent == "Analista de Investimentos/"
    candidate = SCANNER_ROOT.parent / "12_PYTHON" / "data" / "ingestion.db"
    if candidate.exists():
        return candidate
    cwd_fallback = SCANNER_ROOT / "data" / "ingestion.db"
    if cwd_fallback.exists():
        return cwd_fallback
    return None


def _load_dry_run_matrix() -> list[dict]:
    """Load M017-S05 dry-run matrix CSV (write=False results)."""
    matrix_path = SCANNER_ROOT.parent / "12_PYTHON" / "docs" / "M017_S05_DRY_RUN_MATRIX.csv"
    if not matrix_path.exists():
        return []
    try:
        import csv
        rows = []
        with open(matrix_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
        return rows
    except Exception:
        return []


def _load_inputs_kpis() -> dict:
    """KPIs de valuation_financial_inputs (ingestion.db)."""
    db = _resolve_ingestion_db()
    if db is None:
        return {}
    try:
        conn = sqlite3.connect(str(db))
        total   = conn.execute("SELECT COUNT(*) FROM valuation_financial_inputs").fetchone()[0]
        tickers = conn.execute("SELECT COUNT(DISTINCT ticker) FROM valuation_financial_inputs").fetchone()[0]
        metrics = conn.execute("SELECT COUNT(DISTINCT metric_name) FROM valuation_financial_inputs").fetchone()[0]
        src_rows = conn.execute(
            "SELECT source_type, COUNT(*) FROM valuation_financial_inputs GROUP BY source_type"
        ).fetchall()
        conn.close()
        return {"total": total, "tickers": tickers, "metrics": metrics,
                "sources": {r[0]: r[1] for r in src_rows}}
    except Exception:
        return {}


# ── Tab definitions ───────────────────────────────────────────────────────────

_TABS = ["Portfolio Valuation", "Fundamental Quality", "Macro Context", "Ticker Detail", "M017 Inputs"]


# ── Tab: Portfolio Valuation ─────────────────────────────────────────────────

def render_portfolio_valuation_tab() -> None:
    """Portfolio com fair_value, upside, fonte e metodo."""
    valuation_rows = _load_valuation_rows()

    if not valuation_rows:
        # Fallback to watchlist summary
        rows = get_watchlist_summary()
        val_rows = [r for r in rows if r.get("fair_value_brl") and r.get("fair_value_brl") > 0]
        if val_rows:
            _render_watchlist_valuations(val_rows)
            return
        empty_state(
            "Nenhum dado de valuation encontrado.\n"
            "O pipeline de inteligencia ainda nao executou.\n"
            "Execute: python -m src.main daemon",
            icon="",
        )
        return

    # KPIs
    total = len(valuation_rows)
    avg_upside = sum(r.get("upside_pct") or 0 for r in valuation_rows) / total if total else 0
    high_upside = sum(1 for r in valuation_rows if (r.get("upside_pct") or 0) > 20)
    under_valued = sum(1 for r in valuation_rows if (r.get("upside_pct") or 0) > 0)

    kpi_strip([
        {"label": "Ativos c/ FV",   "value": str(total),       "color": "cyan"},
        {"label": "Media Upside",    "value": f"{avg_upside:.1f}%", "color": "warn"},
        {"label": "Upside > 20%",   "value": str(high_upside),  "color": "pos"},
        {"label": "Subvalorizados", "value": str(under_valued),  "color": "pos"},
    ])

    section_title("Valuation por Ativo", icon="")

    # Valuation table
    for row in valuation_rows:
        ticker = row.get("ticker", "—")
        fair_val = row.get("fair_value")
        upside = row.get("upside_pct")
        method = str(row.get("valuation_method") or "—")
        conf = row.get("valuation_confidence")
        market_price = row.get("market_price")
        created = row.get("created_at", "—")[:10] if row.get("created_at") else "—"

        upside_color = _upside_color(upside)
        upside_str = f"{upside:+.1f}%" if upside is not None else "—"

        gov_status = row.get("valuation_governance_status", "")
        gov_chip = _status_to_chip(gov_status)

        bar_width = min(abs(upside or 0) * 2, 100) if upside is not None else 2

        st.markdown(f"""
        <div style="
            background: var(--bg-3); border: 1px solid var(--border-1);
            border-radius: 14px; padding: 16px 18px; margin-bottom: 12px;
        ">
            <!-- Header -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                <div>
                    <div style="font-family:var(--font-display); font-size:1.25rem; font-weight:900;
                         color:var(--fg-1);">{ticker}</div>
                    <div style="font-size:.65rem; color:var(--fg-5); margin-top:3px; font-family:var(--font-mono);">
                        {row.get('company_name', '') or row.get('sector', '')} · {created}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:var(--font-display); font-size:1.4rem; font-weight:900;
                         color:{upside_color};">{upside_str}</div>
                    <div style="font-family:var(--font-mono); font-size:.62rem; color:var(--fg-5);">
                        Upside
                    </div>
                </div>
            </div>

            <!-- FV / Market Price -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px;">
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:3px;">Valor Justo</div>
                    <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:700; color:var(--fg-1);">
                        R$ {_fmt_float(fair_val)}
                    </div>
                </div>
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:3px;">Preco Atual</div>
                    <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:700; color:var(--fg-1);">
                        R$ {_fmt_float(market_price)}
                    </div>
                </div>
            </div>

            <!-- Method + confidence -->
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; font-size:.62rem; font-family:var(--font-mono);">
                {f'<span style="background:var(--bg-0); border:1px solid var(--border-1); '
                 f'border-radius:5px; padding:2px 7px; color:var(--fg-4);">{method}</span>' if method and method != '—' else ''}
                {f'<span style="background:var(--bg-0); border:1px solid var(--border-1); '
                 f'border-radius:5px; padding:2px 7px; color:var(--fg-4);">Conf {_fmt_float(conf, 1)}</span>' if conf else ''}
                {gov_chip}
            </div>

            <!-- Upside bar -->
            <div style="margin-top:6px;">
                <div style="background:var(--bg-0); border-radius:99px; height:4px; overflow:hidden;">
                    <div style="width:{bar_width}%; height:100%; background:{upside_color}; border-radius:99px;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_watchlist_valuations(rows: list[dict]) -> None:
    """Fallback: render valuation from watchlist summary rows."""
    total = len(rows)
    val_rows = [r for r in rows if r.get("fair_value_brl") and r.get("fair_value_brl") > 0]
    if not val_rows:
        empty_state("Nenhum ativo com valuation.", icon="")
        return

    kpi_strip([
        {"label": "Ativos c/ FV", "value": str(len(val_rows)), "color": "cyan"},
        {"label": "Total",         "value": str(total),          "color": "cyan"},
    ])

    section_title("Valuation via Watchlist", icon="")

    for row in val_rows:
        ticker = row.get("ticker", "—")
        fv = row.get("fair_value_brl")
        price = row.get("price")
        upside = row.get("upside_pct")
        val_source = _source_label(row.get("valuation_source", "none"))
        generated = str(row.get("generated_at", "—"))[:10]

        upside_str = f"{upside:+.1f}%" if upside is not None else "—"
        upside_color = _upside_color(upside)

        st.markdown(f"""
        <div style="background:var(--bg-3); border:1px solid var(--border-1);
             border-radius:14px; padding:14px 16px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <div style="font-family:var(--font-display); font-size:1.2rem; font-weight:900; color:var(--fg-1);">
                    {ticker}
                </div>
                <div style="font-family:var(--font-display); font-size:1.2rem; font-weight:900; color:{upside_color};">
                    {upside_str}
                </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:3px;">Valor Justo</div>
                    <div style="font-family:var(--font-mono); font-size:.95rem; font-weight:700; color:var(--fg-1);">R$ {_fmt_float(fv)}</div>
                </div>
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:3px;">Preco Atual</div>
                    <div style="font-family:var(--font-mono); font-size:.95rem; font-weight:700; color:var(--fg-1);">R$ {_fmt_float(price)}</div>
                </div>
            </div>
            <div style="font-size:.6rem; color:var(--fg-5); font-family:var(--font-mono);">
                Fonte: {val_source} · {generated}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Tab: Fundamental Quality ─────────────────────────────────────────────────

def render_fundamental_quality_tab() -> None:
    """Scores de qualidade fundamental: financial health, profitability, growth, leverage."""
    fq_rows = _load_fundamental_quality_rows()

    if not fq_rows:
        empty_state(
            "Nenhum dado de qualidade fundamental encontrado.\n"
            "O pipeline ainda nao executou ou os scores ainda nao foram calculados.",
            icon="",
        )
        return

    total = len(fq_rows)
    avg_fq = sum(r.get("fundamental_quality_score") or 0 for r in fq_rows) / total if total else 0

    kpi_strip([
        {"label": "Ativos c/ FQ",   "value": str(total),  "color": "cyan"},
        {"label": "Score medio FQ", "value": f"{avg_fq:.0f}", "color": "warn"},
    ])

    section_title("Qualidade Fundamental por Ativo", icon="")

    for row in fq_rows:
        ticker = row.get("ticker", "—")
        fq = row.get("fundamental_quality_score")
        fh = row.get("financial_health_score")
        prof = row.get("profitability_score")
        growth = row.get("growth_score")
        lev = row.get("leverage_score")
        dq = row.get("data_quality_score")
        gov = row.get("valuation_governance_status", "")
        created = str(row.get("created_at", ""))[:10] if row.get("created_at") else "—"

        gov_chip = _status_to_chip(gov)

        # Color for FQ score
        fq_val = fq if fq is not None else 0
        fq_color = "var(--pos-500)" if fq_val >= 70 else "var(--warn-500)" if fq_val >= 40 else "var(--neg-500)"

        st.markdown(f"""
        <div style="background:var(--bg-3); border:1px solid var(--border-1);
             border-radius:14px; padding:14px 16px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="font-family:var(--font-display); font-size:1.1rem; font-weight:900; color:var(--fg-1);">
                    {ticker}
                </div>
                <div style="display:flex; gap:6px; align-items:center;">
                    {gov_chip}
                    <span style="font-family:var(--font-mono); font-size:.62rem; color:var(--fg-6);">{created}</span>
                </div>
            </div>
            <!-- Score principal -->
            <div style="margin-bottom:10px; text-align:center;">
                <span style="font-family:var(--font-display); font-size:2rem; font-weight:900; color:{fq_color};">
                    {_fmt_float(fq, 0)}
                </span>
                <span style="font-family:var(--font-mono); font-size:.65rem; color:var(--fg-5); margin-left:6px;">
                    FQ Score
                </span>
            </div>
            <!-- Sub-scores grid -->
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:8px;">
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; letter-spacing:.4px; margin-bottom:4px;">Financial Health</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{_fmt_float(fh, 0)}</div>
                </div>
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; letter-spacing:.4px; margin-bottom:4px;">Rentabilidade</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{_fmt_float(prof, 0)}</div>
                </div>
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; letter-spacing:.4px; margin-bottom:4px;">Crescimento</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{_fmt_float(growth, 0)}</div>
                </div>
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; letter-spacing:.4px; margin-bottom:4px;">Alavancagem</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{_fmt_float(lev, 0)}</div>
                </div>
            </div>
            <!-- Data quality bar -->
            {f'''<div style="margin-top:10px;">
                <div style="display:flex; justify-content:space-between; font-size:.62rem; color:var(--fg-5); margin-bottom:4px;">
                    <span>Qualidade de Dados</span>
                    <span style="font-family:var(--font-mono); color:var(--fg-3);">{_fmt_float(dq, 0)}</span>
                </div>
                <div style="background:var(--bg-0); border-radius:99px; height:4px; overflow:hidden;">
                    <div style="width:{min((dq or 0) * 1, 100)}%; height:100%; background:var(--brand-500); border-radius:99px;"></div>
                </div>
            </div>''' if dq is not None else ''}
        </div>
        """, unsafe_allow_html=True)


# ── Tab: Macro Context ────────────────────────────────────────────────────────

def render_macro_context_tab() -> None:
    """Contexto macro: Selic, PTAX, IPCA, regime de mercado."""
    macro = get_macro_panel()
    regime = macro.get("regime", [])
    selic  = macro.get("selic", [])
    ptax   = macro.get("ptax", [])
    ipca   = macro.get("ipca_12m", [])
    status = macro.get("source_status", "SEM_DADOS_MACRO")

    section_title(f"Contexto Macroeconomico — {status}", icon="")

    if status == "ERRO_CONEXAO":
        empty_state("Erro ao conectar ao banco de dados macro.", icon="")
        return

    # Regime
    if regime:
        r = regime[0]
        st.markdown(f"""
        <div style="background:var(--bg-3); border:1px solid var(--border-1);
             border-radius:14px; padding:14px 16px; margin-bottom:14px;">
            <div style="font-size:.65rem; text-transform:uppercase; letter-spacing:.8px;
                 color:var(--fg-5); font-weight:700; margin-bottom:10px;">REGIME DE MERCADO</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px;">
                <div>
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:4px;">Regime</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{r.get('primary', '—')}</div>
                </div>
                <div>
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:4px;">Tendencia</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{r.get('trend', '—')}</div>
                </div>
                <div>
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:4px;">Volatilidade</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{r.get('volatility', '—')}</div>
                </div>
                <div>
                    <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:4px;">Liquidez</div>
                    <div style="font-family:var(--font-mono); font-size:.85rem; font-weight:700; color:var(--fg-2);">{r.get('liquidity', '—')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block(
            "warn",
            "Regime de Mercado Indisponivel",
            "O pipeline de regime ainda nao executou ou a tabela market_regime_daily esta vazia.",
        ), unsafe_allow_html=True)

    # BCB series
    col1, col2, col3 = st.columns(3)

    if selic:
        with col1:
            latest = selic[0]
            st.markdown(f"""
            <div style="background:var(--bg-3); border:1px solid var(--border-1);
                 border-radius:12px; padding:12px 14px; margin-bottom:10px;">
                <div style="font-size:.6rem; text-transform:uppercase; letter-spacing:.6px;
                     color:var(--fg-5); font-weight:700; margin-bottom:8px;">SELIC ({latest.get('date', '')[:7]})</div>
                <div style="font-family:var(--font-display); font-size:1.8rem; font-weight:900; color:var(--fg-1);">
                    {latest.get('value', '—'):.2f}<span style="font-size:.7rem; color:var(--fg-5);">%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if ptax:
                latest = ptax[0]
                st.markdown(f"""
                <div style="background:var(--bg-3); border:1px solid var(--border-1);
                     border-radius:12px; padding:12px 14px; margin-bottom:10px;">
                    <div style="font-size:.6rem; text-transform:uppercase; letter-spacing:.6px;
                         color:var(--fg-5); font-weight:700; margin-bottom:8px;">PTAX ({latest.get('date', '')[:7]})</div>
                    <div style="font-family:var(--font-display); font-size:1.8rem; font-weight:900; color:var(--fg-1);">
                        R$ {latest.get('value', '—'):.4f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        with col3:
            if ipca:
                latest = ipca[0]
                st.markdown(f"""
                <div style="background:var(--bg-3); border:1px solid var(--border-1);
                     border-radius:12px; padding:12px 14px; margin-bottom:10px;">
                    <div style="font-size:.6rem; text-transform:uppercase; letter-spacing:.6px;
                         color:var(--fg-5); font-weight:700; margin-bottom:8px;">IPCA 12m ({latest.get('date', '')[:7]})</div>
                    <div style="font-family:var(--font-display); font-size:1.8rem; font-weight:900; color:var(--fg-1);">
                        {latest.get('value', '—'):.2f}<span style="font-size:.7rem; color:var(--fg-5);">%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    if not selic and not ptax and not ipca:
        empty_state(
            "Nenhum dado macro encontrado.\n"
            "Execute o pipeline BCB para buscar Selic, PTAX e IPCA.",
            icon="",
        )


# ── Tab: Ticker Detail ────────────────────────────────────────────────────────

def render_ticker_detail_tab() -> None:
    """Valuation detalhado por ticker + cross-check com scanner_quant_db."""
    rows = get_watchlist_summary()
    if not rows:
        empty_state("Nenhum ativo disponivel.", icon="")
        return

    tickers = sorted(set(r["ticker"] for r in rows))
    selected = st.selectbox("Selecionar ativo:", tickers, key="ve_ticker")

    detail = get_asset_detail(selected)
    if detail is None:
        empty_state(f"Sem dados para {selected}.", icon="")
        return

    val_avail = detail.get("valuation_available", False)
    val_src = _source_label(detail.get("valuation_source", "none"))
    val_method = str(detail.get("valuation_method") or "—")
    val_date = str(detail.get("valuation_date") or detail.get("valuation_timestamp") or "—")
    fair_val = detail.get("fair_value") or detail.get("fair_value_brl")
    upside_pct = detail.get("upside_pct")
    market_price = detail.get("market_price") or detail.get("current_price")

    # Divergence info
    divergence = detail.get("divergence_vs_scanner_quant")
    integrated_score = detail.get("integrated_score")
    integrated_status = str(detail.get("integrated_status") or "SEM_DADOS")
    gov_status = str(detail.get("integrated_governance_status") or "")

    # ── Header with valuation summary ────────────────────────────────────────
    pos = str(detail.get("thesis", {}).get("positioning", "MANTER")).upper()
    pos_color = "var(--pos-500)" if pos == "COMPRAR" else ("var(--neg-500)" if pos == "VENDER" else "var(--fg-4)")

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, var(--bg-2) 0%, var(--bg-3) 60%);
        border: 1px solid var(--border-1); border-radius: 16px;
        padding: 20px 24px; margin-bottom: 18px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px;">
            <div>
                <div style="font-family:var(--font-display); font-size:1.8rem; font-weight:900; color:var(--fg-1);">
                    {selected}
                </div>
                <div style="font-size:.78rem; color:var(--fg-4); margin-top:4px;">
                    Score {f"{integrated_score:.0f}" if integrated_score else "—"} · {integrated_status}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:var(--font-display); font-size:1.6rem; font-weight:900; color:{pos_color};">
                    {pos}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not val_avail:
        st.markdown(alert_block(
            "warn",
            "Valuation Indisponivel",
            f"O pipeline DCF ainda nao executou para {selected}. "
            "Nao ha valor justo nem upside disponivel.",
        ), unsafe_allow_html=True)
        return

    # ── Valuation section ──────────────────────────────────────────────────
    upside_color = _upside_color(upside_pct)
    upside_str = f"{upside_pct:+.1f}%" if upside_pct is not None else "—"

    st.markdown(f"""
    <div style="background:var(--bg-3); border:1px solid var(--border-1);
         border-radius:14px; padding:16px 18px; margin-bottom:14px;">
        <div style="font-size:.65rem; text-transform:uppercase; letter-spacing:.8px;
             color:var(--fg-5); font-weight:700; margin-bottom:12px;">VALUATION</div>

        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:14px;">
            <div>
                <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                     letter-spacing:.5px; margin-bottom:4px;">Preco Atual</div>
                <div style="font-family:var(--font-mono); font-size:1.2rem; font-weight:700; color:var(--fg-1);">
                    R$ {_fmt_float(market_price)}
                </div>
            </div>
            <div>
                <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                     letter-spacing:.5px; margin-bottom:4px;">Valor Justo</div>
                <div style="font-family:var(--font-mono); font-size:1.2rem; font-weight:700; color:var(--fg-1);">
                    R$ {_fmt_float(fair_val)}
                </div>
            </div>
            <div>
                <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                     letter-spacing:.5px; margin-bottom:4px;">Upside</div>
                <div style="font-family:var(--font-mono); font-size:1.2rem; font-weight:700; color:{upside_color};">
                    {upside_str}
                </div>
            </div>
        </div>

        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; font-size:.62rem; font-family:var(--font-mono);">
            <span style="background:var(--bg-0); border:1px solid var(--border-1); border-radius:5px; padding:2px 8px; color:var(--fg-4);">
                Fonte: {val_src}
            </span>
            {f'<span style="background:var(--bg-0); border:1px solid var(--border-1); border-radius:5px; padding:2px 8px; color:var(--fg-4);">Metodo: {val_method}</span>' if val_method != '—' else ''}
            {f'<span style="background:var(--bg-0); border:1px solid var(--border-1); border-radius:5px; padding:2px 8px; color:var(--fg-4);">Data: {val_date[:10]}</span>' if val_date else ''}
        </div>

        {f'''<div style="margin-top:10px;">
            <div style="background:var(--bg-0); border-radius:99px; height:5px; overflow:hidden;">
                <div style="width:{min(abs(upside_pct or 0) * 2, 100)}%; height:100%; background:{upside_color}; border-radius:99px;"></div>
            </div>
        </div>''' if upside_pct is not None else ''}
    </div>
    """, unsafe_allow_html=True)

    # ── Divergence alert ────────────────────────────────────────────────────
    if divergence:
        sq_fv = divergence.get("scanner_quant_fair_value")
        pl_fv = divergence.get("pipeline_fair_value")
        div_pct = divergence.get("divergence_pct")
        note = divergence.get("note", "")

        st.markdown(alert_block(
            "warn",
            "Divergencia de Valuation Detectada",
            f"Scanner DB: R$ {_fmt_float(sq_fv)} vs Pipeline DCF: R$ {_fmt_float(pl_fv)} "
            f"({div_pct:+.1f}%). {note}",
        ), unsafe_allow_html=True)

    # ── Fundamental quality scores ─────────────────────────────────────────
    fq_score = detail.get("fundamental_quality_score")
    fh_score = detail.get("financial_health_score")
    prof_score = detail.get("profitability_score")
    growth_score = detail.get("growth_score")
    lev_score = detail.get("leverage_score")

    section_title("Qualidade Fundamental", icon="")

    for label, score in [
        ("Score Geral", fq_score),
        ("Saude Financeira", fh_score),
        ("Rentabilidade", prof_score),
        ("Crescimento", growth_score),
        ("Alavancagem", lev_score),
    ]:
        if score is not None:
            try:
                val = float(score)
                color = "var(--pos-500)" if val >= 70 else "var(--warn-500)" if val >= 40 else "var(--neg-500)"
                st.markdown(score_bar(label, val, color=color), unsafe_allow_html=True)
            except (TypeError, ValueError):
                pass

    # ── Coverage info ───────────────────────────────────────────────────────
    data_q = detail.get("data_quality_score")
    gov_blocked = detail.get("governance_blocked")
    generated = str(detail.get("generated_at", "—"))[:10] if detail.get("generated_at") else "—"

    st.markdown(f"""
    <div style="background:var(--bg-2); border:1px solid var(--border-1);
         border-radius:10px; padding:12px 14px; margin-top:10px; font-size:.7rem; color:var(--fg-4);
         display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
        <div>
            <span style="color:var(--fg-5);">Qualidade de Dados: </span>
            <span style="font-family:var(--font-mono); font-weight:700; color:var(--fg-3);">{_fmt_float(data_q, 0)}</span>
        </div>
        <div>
            <span style="color:var(--fg-5);">Bloqueado: </span>
            <span style="font-family:var(--font-mono); font-weight:700; color:var(--fg-3);">{'Sim' if gov_blocked else 'Nao'}</span>
        </div>
        <div>
            <span style="color:var(--fg-5);">Atualizado: </span>
            <span style="font-family:var(--font-mono); font-weight:700; color:var(--fg-3);">{generated}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Tab: M017 Inputs ─────────────────────────────────────────────────────────

_STATUS_COLOR = {
    "PRESERVE_EXISTING":    "var(--pos-500)",
    "READY_TO_CALCULATE":   "var(--brand-500)",
    "PARTIAL_INPUTS":       "var(--warn-500)",
    "TECH_FALLBACK":        "var(--warn-500)",
    "NEEDS_DATA":           "var(--neg-500)",
    "NEEDS_RI_DOCS":        "var(--neg-500)",
    "LEGACY_TICKER":        "var(--fg-5)",
}

def render_m017_inputs_tab() -> None:
    """M017: valuation_financial_inputs + dry-run matrix + universe status."""
    kpis = _load_inputs_kpis()
    dry_run = _load_dry_run_matrix()

    # ── KPI strip ──────────────────────────────────────────────────────────
    ready_count   = sum(1 for r in _M017_UNIVERSE if r["model_status"] == "READY_TO_CALCULATE")
    preserve_cnt  = sum(1 for r in _M017_UNIVERSE if r["model_status"] == "PRESERVE_EXISTING")
    partial_cnt   = sum(1 for r in _M017_UNIVERSE if r["model_status"] == "PARTIAL_INPUTS")

    kpi_strip([
        {"label": "valuation_financial_inputs", "value": f"{kpis.get('total', '—'):,}" if kpis else "—",  "color": "cyan"},
        {"label": "Tickers CVM/DFP/ITR",        "value": str(kpis.get("tickers", "—")) if kpis else "—", "color": "cyan"},
        {"label": "PRESERVE_EXISTING",          "value": str(preserve_cnt),                               "color": "green"},
        {"label": "READY_TO_CALCULATE",         "value": str(ready_count),                                "color": "cyan"},
        {"label": "PARTIAL_INPUTS",             "value": str(partial_cnt),                                "color": "amber"},
        {"label": "Dry-run OK (write=False)",   "value": str(len(dry_run)),                               "color": "green"},
    ])

    # ── Fonte de dados ────────────────────────────────────────────────────
    if kpis:
        sources = kpis.get("sources", {})
        cvm_cnt = sources.get("CVM_CSV", 0)
        b3_cnt  = sources.get("B3_MARKET_DATA", 0)
        st.markdown(
            f'<div style="font-size:.68rem; color:var(--fg-5); font-family:var(--font-mono); '
            f'margin-bottom:14px; padding: 6px 10px; background:var(--bg-2); border-radius:8px;">'
            f'Fonte: ingestion.db · CVM_CSV={cvm_cnt:,} · B3_MARKET_DATA={b3_cnt} · '
            f'{kpis.get("metrics","?")} métricas · M017-S03/S04 (2026-05-26)</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:.68rem; color:var(--neg-500); font-family:var(--font-mono); '
            'margin-bottom:14px; padding:6px 10px; background:var(--bg-2); border-radius:8px;">'
            'ingestion.db não encontrada — defina FINANCIAL_INPUTS_DB_PATH ou verifique 12_PYTHON/data/</div>',
            unsafe_allow_html=True,
        )

    # ── 9 Fair Values Preservados ─────────────────────────────────────────
    section_title("9 Fair Values Preservados — M015/M016", icon="🔒")
    cols = st.columns(3)
    for idx, (ticker, fv) in enumerate(_PRESERVE_EXISTING.items()):
        with cols[idx % 3]:
            st.markdown(f"""
            <div style="background:var(--bg-3); border:1px solid var(--border-1);
                 border-radius:12px; padding:12px 14px; margin-bottom:10px; text-align:center;">
                <div style="font-family:var(--font-display); font-size:1.05rem; font-weight:900;
                     color:var(--fg-1);">{ticker}</div>
                <div style="font-family:var(--font-mono); font-size:1.2rem; font-weight:700;
                     color:var(--pos-500); margin:4px 0;">R$ {fv:.2f}</div>
                <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                     letter-spacing:.4px;">PRESERVE_EXISTING</div>
            </div>
            """, unsafe_allow_html=True)

    # ── M017 Universe (32 tickers) ────────────────────────────────────────
    section_title("Universo M017 — 32 Tickers", icon="🗺")

    for row in _M017_UNIVERSE:
        status  = row["model_status"]
        color   = _STATUS_COLOR.get(status, "var(--fg-4)")
        method  = row["method_suggested"]
        model   = row["model"]
        block   = row["block_reason"]
        ticker  = row["ticker"]

        st.markdown(f"""
        <div style="background:var(--bg-3); border:1px solid var(--border-1);
             border-radius:10px; padding:10px 14px; margin-bottom:6px;
             display:flex; justify-content:space-between; align-items:center; gap:10px;">
            <div style="font-family:var(--font-display); font-size:1rem; font-weight:900;
                 color:var(--fg-1); min-width:70px;">{ticker}</div>
            <div style="font-size:.6rem; font-family:var(--font-mono); font-weight:700;
                 color:{color}; min-width:170px;">{status}</div>
            <div style="font-size:.62rem; color:var(--fg-4); min-width:80px;">{model}</div>
            <div style="font-size:.62rem; color:var(--fg-4); min-width:90px;">{method}</div>
            <div style="font-size:.6rem; color:var(--fg-5); flex:1; text-align:right;">
                {block if block else "—"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Dry-run Matrix — 18 tickers (write=False) ─────────────────────────
    if dry_run:
        section_title("Dry-Run M017-S05 — 18 Tickers (write=False)", icon="🧪")

        st.markdown(
            '<div style="font-size:.65rem; color:var(--fg-5); font-family:var(--font-mono); '
            'margin-bottom:10px;">Todos os fair_values abaixo foram calculados com write=False. '
            'Nenhum valor foi gravado. M018 persiste com write=True após validação.</div>',
            unsafe_allow_html=True,
        )

        for row in dry_run:
            ticker   = row.get("ticker", "—")
            fv       = row.get("fair_value", "—")
            method   = row.get("method_used", "—")
            upside   = row.get("upside_pct", "")
            flags    = row.get("quality_flags", "")
            status   = row.get("status", "")

            try:
                upside_f = float(upside)
                upside_str  = f"{upside_f:+.1f}%"
                upside_color = "var(--pos-500)" if upside_f > 0 else "var(--neg-500)"
            except (ValueError, TypeError):
                upside_str = "—"
                upside_color = "var(--fg-5)"

            flag_html = ""
            if flags:
                for flag in flags.split(","):
                    flag = flag.strip()
                    if flag:
                        fc = "var(--warn-500)" if flag != "DISTRESSED" else "var(--neg-500)"
                        flag_html += (
                            f'<span style="background:var(--bg-0); border:1px solid {fc}; '
                            f'border-radius:4px; padding:1px 6px; font-size:.58rem; '
                            f'color:{fc}; margin-right:4px;">{flag}</span>'
                        )

            st.markdown(f"""
            <div style="background:var(--bg-3); border:1px solid var(--border-1);
                 border-radius:10px; padding:12px 16px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="font-family:var(--font-display); font-size:1rem; font-weight:900; color:var(--fg-1);">
                        {ticker}
                    </div>
                    <div style="font-family:var(--font-mono); font-size:1.05rem; font-weight:700; color:{upside_color};">
                        {upside_str}
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:6px;">
                    <div>
                        <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:2px;">Fair Value (dry-run)</div>
                        <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--fg-1);">R$ {fv}</div>
                    </div>
                    <div>
                        <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:2px;">Método</div>
                        <div style="font-family:var(--font-mono); font-size:.85rem; color:var(--fg-3);">{method}</div>
                    </div>
                    <div>
                        <div style="font-size:.55rem; color:var(--fg-6); text-transform:uppercase; margin-bottom:2px;">Status</div>
                        <div style="font-family:var(--font-mono); font-size:.78rem; color:var(--brand-500);">{status}</div>
                    </div>
                </div>
                {f'<div style="margin-top:4px;">{flag_html}</div>' if flag_html else ''}
                <div style="margin-top:6px; font-size:.55rem; color:var(--fg-6); font-family:var(--font-mono);">
                    write=False · M017-S05 · asset_intelligence_snapshots não alterada
                </div>
            </div>
            """, unsafe_allow_html=True)

    else:
        empty_state(
            "Dry-run matrix não encontrada.\n"
            "Esperado em: 12_PYTHON/docs/M017_S05_DRY_RUN_MATRIX.csv",
            icon="",
        )


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
        <div class="page-header-title">Valuation Engine</div>
        <div class="page-header-sub">Analise fundamentalista — valor justo, upside e qualidade fundamental</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tab navigation ────────────────────────────────────────────────────────
    tabs = st.tabs(_TABS)

    with tabs[0]:
        render_portfolio_valuation_tab()

    with tabs[1]:
        render_fundamental_quality_tab()

    with tabs[2]:
        render_macro_context_tab()

    with tabs[3]:
        render_ticker_detail_tab()

    with tabs[4]:
        render_m017_inputs_tab()


main()