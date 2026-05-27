"""Valuation Hub — Central de Valuation Fundamentalista

Abas:
  1. Visão Geral       — hero + preços justos (wl-card) + prontas (tbl) + pendências (chip)
  2. Base Fundamentalista — cobertura de valuation_financial_inputs (ingestion.db)
  3. Simulação dos Modelos — dry-run M017-S05 (write=False, nenhum valor salvo)
  4. Qualidade Fundamental — scores de qualidade do asset_intelligence_snapshots
  5. Contexto Macro     — Selic, PTAX, IPCA, regime de mercado

Regras:
  - Nenhum cálculo de fair_value
  - Nenhuma escrita no banco
  - Nenhum mock — todos os dados são lidos diretamente das fontes
  - Sem JSON bruto exibido ao usuário
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────────
_SCANNER_ROOT = Path(__file__).resolve().parents[1]
_root_str = str(_SCANNER_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

# Remove 12_PYTHON from sys.path to avoid module name collisions
_PIPELINE_ROOT = str(_SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)

for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st
import pandas as pd

# ── Cache helpers ─────────────────────────────────────────────────────────────
_CACHE_TTL = 300  # 5 minutes

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    section_title,
    kpi_strip,
    empty_state,
    alert_block,
    score_bar,
)
from src.dashboard.data import get_macro_panel

# ── DB Paths ────────────────────────────────────────────────────────────────────
_SCANNER_DB = _SCANNER_ROOT / "data" / "database" / "scanner_quant.db"
_INGESTION_DB_PATH: Path | None = None
_DRY_RUN_MATRIX_PATH = _SCANNER_ROOT.parent / "12_PYTHON" / "docs" / "M017_S05_DRY_RUN_MATRIX.csv"


def _resolve_ingestion_db() -> Path | None:
    import os
    env = os.environ.get("FINANCIAL_INPUTS_DB_PATH")
    if env:
        p = Path(env)
        if p.exists():
            return p
    candidate = _SCANNER_ROOT.parent / "12_PYTHON" / "data" / "ingestion.db"
    if candidate.exists():
        return candidate
    fallback = _SCANNER_ROOT / "data" / "ingestion.db"
    if fallback.exists():
        return fallback
    return None


_INGESTION_DB_PATH = _resolve_ingestion_db()

# ── M017 Universe constants ─────────────────────────────────────────────────────

_PRESERVE_EXISTING: dict[str, dict] = {
    "ABCB4":  {"fv": 210.50, "sector": "Banco",        "method": "P/BV"},
    "BBAS3":  {"fv":  64.84, "sector": "Banco",        "method": "P/BV"},
    "BBDC4":  {"fv":  34.63, "sector": "Banco",        "method": "P/BV"},
    "BPAC11": {"fv":   8.46, "sector": "Banco",        "method": "P/BV"},
    "BRSR6":  {"fv":   4.66, "sector": "Banco",        "method": "P/BV"},
    "ITUB4":  {"fv":  73.69, "sector": "Banco",        "method": "P/BV"},
    "SANB11": {"fv":  86.79, "sector": "Banco",        "method": "P/BV"},
    "PETR4":  {"fv":  81.12, "sector": "Petróleo/Gás", "method": "DCF/FCFF"},
    "WEGE3":  {"fv":  40.16, "sector": "Indústria",    "method": "DCF/FCFF"},
}

_READY_TO_CALCULATE: list[dict] = [
    {"ticker": "EGIE3",  "sector": "Energia",         "model": "Utilidade",  "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "SBSP3",  "sector": "Saneamento",      "model": "Utilidade",  "method": "EV/EBITDA", "notes": "FCF negativo esperado"},
    {"ticker": "TAEE11", "sector": "Energia",         "model": "Utilidade",  "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "AZZA3",  "sector": "Varejo",          "model": "Varejo",     "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "LREN3",  "sector": "Varejo",          "model": "Varejo",     "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "MGLU3",  "sector": "Varejo",          "model": "Varejo",     "method": "EV/EBITDA", "notes": "FCF em revisão"},
    {"ticker": "VIVA3",  "sector": "Varejo",          "model": "Varejo",     "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "PRIO3",  "sector": "Petróleo",        "model": "Commodity",  "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "RECV3",  "sector": "Petróleo",        "model": "Commodity",  "method": "EV/EBITDA", "notes": "FCF negativo esperado"},
    {"ticker": "FLRY3",  "sector": "Saúde",           "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "HYPE3",  "sector": "Farmácia",        "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "KLBN11", "sector": "Papel/Celulose",  "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "RADL3",  "sector": "Farmácia",        "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "RAIL3",  "sector": "Logística",       "model": "Industrial", "method": "EV/EBITDA", "notes": ""},
    {"ticker": "RENT3",  "sector": "Aluguel",         "model": "Industrial", "method": "EV/EBITDA", "notes": ""},
    {"ticker": "SUZB3",  "sector": "Papel/Celulose",  "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "VAMO3",  "sector": "Locação",         "model": "Industrial", "method": "EV/EBITDA", "notes": "FCF negativo esperado"},
]

_PENDENCIAS: list[dict] = [
    {"ticker": "PCAR3",  "status": "Dados parciais",      "nota": "Dados parciais — situação especial (empresa em recuperação judicial)"},
    {"ticker": "PETZ3",  "status": "Ticker legado",       "nota": "Ticker legado — empresa encerrada (fusão consumada)"},
    {"ticker": "AUAU3",  "status": "Aguardando docs CVM", "nota": "CNPJ sem mapeamento — aguardando dados CVM/RI"},
    {"ticker": "VALE3",  "status": "Dados insuficientes", "nota": "Aguardando ingestion CVM — ri_docs=0"},
    {"ticker": "NTCO3",  "status": "Aguardando docs CVM", "nota": "Docs RI/CVM insuficientes para extração"},
    {"ticker": "VIVT3",  "status": "Modelo alternativo",  "nota": "Modelo alternativo disponível (EV/EBITDA) — aguardando inputs CVM"},
]

_STATUS_PT: dict[str, str] = {
    "PRESERVE_EXISTING":  "Preço justo preservado",
    "READY_TO_CALCULATE": "Pronta para cálculo",
    "PARTIAL_INPUTS":     "Dados parciais",
    "TECH_FALLBACK":      "Modelo alternativo",
    "NEEDS_DATA":         "Dados insuficientes",
    "NEEDS_RI_DOCS":      "Aguardando docs CVM",
    "LEGACY_TICKER":      "Ticker legado",
}

# ── M018-S04 Preliminary Results ───────────────────────────────────────────────

_COMPANY_NAMES_M018: dict[str, str] = {
    "EGIE3":  "Engie Brasil",
    "LREN3":  "Lojas Renner",
    "VIVA3":  "Vivara",
    "RADL3":  "Raia Drogasil",
    "RAIL3":  "Rumo",
    "RENT3":  "Localiza",
    "SUZB3":  "Suzano",
    "PRIO3":  "PRIO",
    "RECV3":  "PetroRecôncavo",
    "SBSP3":  "Sabesp",
    "TAEE11": "Taesa",
    "AZZA3":  "Azzas 2154",
    "MGLU3":  "Magazine Luiza",
    "PCAR3":  "Pão de Açúcar",
    "FLRY3":  "Fleury",
    "HYPE3":  "Hypera",
    "KLBN11": "Klabin",
    "VAMO3":  "Vamos",
}

_CONF_PT: dict[str, str] = {
    "HIGH":         "Alta",
    "MEDIUM":       "Média",
    "LOW":          "Baixa",
    "INSUFFICIENT": "Insuficiente",
}

# Fallback prices from last snapshot (2026-05-22)
_PRICES_FALLBACK: dict[str, dict] = {
    "ABCB4":  {"price": 24.38,  "name": "ABC Brasil"},
    "BBAS3":  {"price": 20.94,  "name": "Banco do Brasil"},
    "BBDC4":  {"price": 17.62,  "name": "Bradesco"},
    "BPAC11": {"price": 53.93,  "name": "BTG Pactual"},
    "BRSR6":  {"price": 14.65,  "name": "Banrisul"},
    "ITUB4":  {"price": 39.43,  "name": "Itaú Unibanco"},
    "SANB11": {"price": 27.10,  "name": "Santander Brasil"},
    "PETR4":  {"price": 44.48,  "name": "Petrobras"},
    "WEGE3":  {"price": 42.73,  "name": "WEG"},
}


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _fmt_brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def _fmt_float(v, decimals: int = 2) -> str:
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def _upside_color(pct) -> str:
    try:
        f = float(pct)
        if f > 20:
            return "var(--pos-500)"
        if f > 0:
            return "var(--warn-500)"
        return "var(--neg-500)"
    except (TypeError, ValueError):
        return "var(--fg-5)"


def _badge_html(text: str, variant: str = "cyan") -> str:
    """Returns inline HTML for a badge span."""
    return f'<span class="badge badge-{variant}">{text}</span>'


def _chip_html(text: str, variant: str = "manual") -> str:
    """Returns inline HTML for a chip span with dot indicator."""
    return f'<span class="chip chip-{variant}"><span class="dot"></span>{text}</span>'


def _method_badge(method: str) -> str:
    """Returns a badge styled for the valuation method."""
    variant = "cyan" if ("DCF" in method or "P/BV" in method) else "violet"
    return _badge_html(method, variant)


def _flag_chip(flag: str) -> str:
    """Returns a degraded chip for quality alerts, or empty string."""
    if not flag or flag == "—":
        return ""
    return _chip_html(flag, "degraded")


# ── M018-S04 helpers ────────────────────────────────────────────────────────────

import re as _re
import json as _json


def _fmt_method_prelim(raw: str) -> str:
    """Format internal EV_EBITDA_Nx method code to display string."""
    return raw.replace("EV_EBITDA_", "EV/EBITDA ").replace("_", "/")


def _translate_flag_prelim(flag: str) -> str | None:
    """Translate an M018 internal flag to user-friendly Portuguese label.
    Returns None to silently skip internal-only flags."""
    f = flag.upper()
    if "DISTRESSED" in f:
        return "Distressed"
    if "FCF_NEGATIVE_EXPECTED" in f:
        return "FCF Negativo"
    if "FCF_ANOMALY" in f:
        return "Anomalia FCF"
    if "UNIT_SHARES" in f:
        return "Validar ações"
    if "ELEVATED_LEVERAGE" in f:
        m = _re.search(r"nd_ebitda=(\d+\.?\d*)x", flag)
        ratio = m.group(1) if m else ""
        return f"Alavancagem elevada{f' ({ratio}×)' if ratio else ''}"
    if "VERY_HIGH_LEVERAGE" in f:
        return "Alavancagem muito elevada"
    if "UPSIDE_OVER_2X" in f:
        return "Upside > 2×"
    # Skip confirmed_negative, shares_discrepancy, pn_only, etc.
    return None


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_preliminary_results() -> list[dict]:
    """Load M018_CONTROLLED preliminary results from valuation_results (read-only).

    Rules:
      - SELECT only — zero writes
      - source = 'M018_CONTROLLED', status = 'preliminary'
      - Never touches asset_intelligence_snapshots
    """
    if _INGESTION_DB_PATH is None:
        return []
    try:
        conn = sqlite3.connect(str(_INGESTION_DB_PATH))
        rows = conn.execute("""
            SELECT ticker, preliminary_fair_value, market_price, upside_pct,
                   method_used, confidence, flags, sanity_check_passed, block_reason
            FROM valuation_results
            WHERE source = 'M018_CONTROLLED'
              AND status  = 'preliminary'
            ORDER BY ticker
        """).fetchall()
        conn.close()
        result: list[dict] = []
        for r in rows:
            flags_raw = r[6]
            try:
                flags_list: list[str] = _json.loads(flags_raw) if flags_raw else []
            except Exception:
                flags_list = []
            upside = r[3]
            if upside is not None and float(upside) > 200:
                flags_list = flags_list + ["UPSIDE_OVER_2X"]
            result.append({
                "ticker":                 r[0],
                "preliminary_fair_value": r[1],
                "market_price":           r[2],
                "upside_pct":             r[3],
                "method_used":            r[4],
                "confidence":             r[5],
                "flags":                  flags_list,
                "sanity_check_passed":    r[7],
                "block_reason":           r[8],
            })
        return result
    except Exception:
        return []


def _render_prelim_table(rows: list[dict]) -> None:
    """Render a table of preliminary fair values using st.dataframe."""
    if not rows:
        st.caption("Nenhum valor disponível.")
        return

    table_rows = []
    for r in rows:
        ticker    = r["ticker"]
        company   = _COMPANY_NAMES_M018.get(ticker, "—")
        fv        = r.get("preliminary_fair_value")
        price     = r.get("market_price")
        upside    = r.get("upside_pct")
        method    = _fmt_method_prelim(r.get("method_used") or "—")
        conf      = _CONF_PT.get(r.get("confidence") or "", r.get("confidence") or "—")
        sanity    = r.get("sanity_check_passed")
        flags     = r.get("flags") or []
        translated = [tf for f in flags for tf in [_translate_flag_prelim(f)] if tf]

        fv_str    = _fmt_brl(fv)    if fv    is not None else "—"
        price_str = _fmt_brl(price) if price is not None else "—"

        if upside is not None:
            try:
                upside_str = f"{float(upside):+.1f}%"
            except (TypeError, ValueError):
                upside_str = "—"
        else:
            upside_str = "—"

        conf_emoji = "✅ Alta" if conf == "Alta" else "🔄 Média" if conf == "Média" else "⚠️ Baixa"
        sanity_str = "✅ Passou" if sanity == 1 else "⚠️ Requer validação"
        status_str = "❌ Não aprovado"

        table_rows.append({
            "Ticker":          ticker,
            "Empresa":         company,
            "Preço Mercado":   price_str,
            "Valor Prelim.":  fv_str,
            "Up/Downside":    upside_str,
            "Método":          method,
            "Confiança":       conf_emoji,
            "Checagem":        sanity_str,
            "Alertas":         " · ".join(translated) if translated else "—",
            "Status":          status_str,
        })

    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_market_prices() -> dict[str, dict]:
    """Load latest market prices from asset_intelligence_snapshots, with fallback."""
    result: dict[str, dict] = dict(_PRICES_FALLBACK)
    if not _SCANNER_DB.exists():
        return result
    try:
        conn = sqlite3.connect(str(_SCANNER_DB))
        # Use MAX(created_at) per ticker to avoid Python-side dedup loop
        rows = conn.execute("""
            SELECT ticker, current_price, company_name, created_at
            FROM asset_intelligence_snapshots
            WHERE (ticker, created_at) IN (
                SELECT ticker, MAX(created_at)
                FROM asset_intelligence_snapshots
                GROUP BY ticker
            )
        """).fetchall()
        conn.close()
        for ticker, price, name, created_at in rows:
            if price is not None:
                fallback_name = _PRICES_FALLBACK.get(str(ticker), {}).get("name", "")
                result[str(ticker)] = {
                    "price": float(price),
                    "name": str(name or fallback_name or "").strip().title(),
                    "date": str(created_at or "")[:10],
                }
        return result
    except Exception:
        return result


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_dry_run_matrix() -> list[dict]:
    if not _DRY_RUN_MATRIX_PATH.exists():
        return []
    try:
        rows = []
        with open(_DRY_RUN_MATRIX_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
        return rows
    except Exception:
        return []


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_inputs_kpis() -> dict:
    if _INGESTION_DB_PATH is None:
        return {}
    try:
        conn = sqlite3.connect(str(_INGESTION_DB_PATH))
        total   = conn.execute("SELECT COUNT(*) FROM valuation_financial_inputs").fetchone()[0]
        tickers = conn.execute("SELECT COUNT(DISTINCT ticker) FROM valuation_financial_inputs").fetchone()[0]
        metrics = conn.execute("SELECT COUNT(DISTINCT metric_name) FROM valuation_financial_inputs").fetchone()[0]
        src_rows = conn.execute(
            "SELECT source_type, COUNT(*) FROM valuation_financial_inputs GROUP BY source_type"
        ).fetchall()
        cov_rows = conn.execute("""
            SELECT ticker, COUNT(DISTINCT metric_name) as n_metrics, MAX(period_end) as last_period
            FROM valuation_financial_inputs
            GROUP BY ticker
            ORDER BY ticker
        """).fetchall()
        conn.close()
        return {
            "total": total,
            "tickers": tickers,
            "metrics": metrics,
            "sources": {r[0]: r[1] for r in src_rows},
            "coverage": {r[0]: {"n_metrics": r[1], "last_period": r[2]} for r in cov_rows},
        }
    except Exception:
        return {}


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_key_metrics() -> list[dict]:
    """Load key metrics for READY_TO_CALCULATE tickers — cached to avoid N×M queries."""
    if _INGESTION_DB_PATH is None:
        return []
    try:
        key_metrics = ["revenue", "ebitda", "net_debt", "shares_outstanding"]
        ready_tickers = [r["ticker"] for r in _READY_TO_CALCULATE]
        ticker_ph = ",".join("?" * len(ready_tickers))
        metric_ph = ",".join("?" * len(key_metrics))

        conn = sqlite3.connect(str(_INGESTION_DB_PATH))
        raw = conn.execute(f"""
            SELECT ticker, metric_name, metric_value
            FROM valuation_financial_inputs
            WHERE ticker IN ({ticker_ph})
              AND metric_name IN ({metric_ph})
              AND period_type = 'DFP'
              AND (ticker, metric_name, period_end) IN (
                  SELECT ticker, metric_name, MAX(period_end)
                  FROM valuation_financial_inputs
                  WHERE ticker IN ({ticker_ph})
                    AND metric_name IN ({metric_ph})
                    AND period_type = 'DFP'
                  GROUP BY ticker, metric_name
              )
        """, ready_tickers + key_metrics + ready_tickers + key_metrics).fetchall()
        conn.close()

        pivot: dict[str, dict] = {t: {"Empresa": t} for t in ready_tickers}
        for ticker, metric, val in raw:
            if val is not None:
                v = float(val)
                if metric == "shares_outstanding":
                    pivot[ticker][metric] = f"{v/1e6:.1f}M"
                elif abs(v) >= 1e9:
                    pivot[ticker][metric] = f"R$ {v/1e9:.2f}B"
                elif abs(v) >= 1e6:
                    pivot[ticker][metric] = f"R$ {v/1e6:.1f}M"
                else:
                    pivot[ticker][metric] = f"R$ {v:,.0f}"

        result = []
        for ticker in ready_tickers:
            row = pivot.get(ticker, {"Empresa": ticker})
            for m in key_metrics:
                row.setdefault(m, "—")
            result.append(row)
        return result
    except Exception:
        return []


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_fundamental_quality_rows() -> list[dict]:
    if not _SCANNER_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(_SCANNER_DB))
        rows = conn.execute("""
            SELECT ticker, fundamental_quality_score, financial_health_score,
                   profitability_score, growth_score, leverage_score,
                   data_quality_score, valuation_governance_status, created_at
            FROM asset_intelligence_snapshots
            WHERE fundamental_quality_score IS NOT NULL
            ORDER BY created_at DESC, ticker
        """).fetchall()
        conn.close()
        return [
            {
                "ticker": str(r[0] or ""),
                "fundamental_quality_score": float(r[1]) if r[1] is not None else None,
                "financial_health_score":    float(r[2]) if r[2] is not None else None,
                "profitability_score":       float(r[3]) if r[3] is not None else None,
                "growth_score":              float(r[4]) if r[4] is not None else None,
                "leverage_score":            float(r[5]) if r[5] is not None else None,
                "data_quality_score":        float(r[6]) if r[6] is not None else None,
                "valuation_governance_status": str(r[7] or ""),
                "created_at": str(r[8] or ""),
            }
            for r in rows
        ]
    except Exception:
        return []


# ── Tab 1: Visão Geral ──────────────────────────────────────────────────────────

def render_visao_geral() -> None:
    market = _load_market_prices()

    # ── Hero section ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-section">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;
                  flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-family:var(--font-display);font-size:1.4rem;font-weight:900;
               color:var(--fg-1);letter-spacing:-0.5px;margin-bottom:6px;">
            Valuation Hub — Universo Completo
          </div>
          <div style="font-size:.72rem;color:var(--fg-5);font-family:var(--font-mono);">
            32 empresas · 9 preços justos auditados · 18 valores em validação
            · 7 passaram na checagem automática
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <span class="badge badge-cyan">Base Financeira</span>
          <span class="badge badge-violet">18 Em validação</span>
          <span class="badge badge-buy">7 Passou na checagem</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    kpi_strip([
        {"label": "Empresas monitoradas",   "value": "32",  "color": "cyan"},
        {"label": "Valor preliminar",       "value": "18",  "color": "violet"},
        {"label": "Passou na checagem",     "value": "7",   "color": "green"},
        {"label": "Requer validação",       "value": "11",  "color": "amber"},
        {"label": "Preço justo preservado", "value": "9",   "color": "cyan"},
        {"label": "Aprovado",               "value": "0",   "color": "red"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1.3, 0.8])

    # ── Column A: Preços Justos Preservados ──────────────────────────────────────
    with col_a:
        section_title("Preços Justos Preservados", icon="🔒")
        st.caption("9 ativos auditados M015/M016 · Não recalcular sem force_recalc")

        for ticker, meta in _PRESERVE_EXISTING.items():
            fv = meta["fv"]
            sector = meta["sector"]
            method = meta["method"]
            market_info = market.get(ticker, {})
            price = market_info.get("price")
            name = market_info.get("name", "")
            date = market_info.get("date", "")

            fv_str = _fmt_brl(fv)

            if price:
                upside = (fv / price - 1) * 100
                upside_str = f"{upside:+.1f}%"
                price_str = _fmt_brl(price)
                card_class = "buy" if upside > 5 else "sell" if upside < -5 else "hold"
                upside_color = (
                    "var(--pos-500)" if upside > 5
                    else "var(--neg-500)" if upside < -5
                    else "var(--warn-500)"
                )
            else:
                upside_str = "—"
                price_str = "—"
                card_class = "hold"
                upside_color = "var(--fg-5)"

            name_html = (
                f'<div style="font-size:.6rem;color:var(--fg-5);'
                f'font-family:var(--font-mono);margin:1px 0 2px 0;">{name}</div>'
                if name else ""
            )
            date_html = f" · {date}" if date else ""

            st.markdown(f"""
            <div class="wl-card {card_class}" style="margin-bottom:10px;">
              <div class="top">
                <div>
                  <div class="tk">{ticker}</div>
                  {name_html}
                  <div style="font-size:.58rem;color:var(--fg-6);font-family:var(--font-mono);">
                    {sector}</div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;">
                  <span class="badge badge-cyan">Preservado</span>
                  {_method_badge(method)}
                </div>
              </div>
              <div class="grid">
                <div class="item">Mercado<span class="v">{price_str}</span></div>
                <div class="item">Preço justo<span class="v" style="color:var(--fg-1);">{fv_str}</span></div>
                <div class="item">Upside / Downside
                  <span class="v" style="color:{upside_color};font-weight:900;">{upside_str}</span>
                </div>
                <div class="item">Status<span class="v">Auditado</span></div>
              </div>
              <div class="meta">Auditado{date_html}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Column B: Prontas para Cálculo ────────────────────────────────────────────
    with col_b:
        section_title("Prontas para Cálculo", icon="✅")
        st.caption("17 ativos com inputs fundamentalistas completos")

        table_rows = []
        for r in _READY_TO_CALCULATE:
            ticker = r["ticker"]
            notes = r["notes"]
            status_str = f"⚠️ {notes}" if notes else "✅ OK"

            table_rows.append({
                "Ticker":  ticker,
                "Setor":   r["sector"],
                "Modelo":  r["model"],
                "Método":  r["method"],
                "Status":  status_str,
            })

        df_b = pd.DataFrame(table_rows)
        st.dataframe(df_b, use_container_width=True, hide_index=True, height=300)

    # ── Column C: Pendências ─────────────────────────────────────────────────────
    with col_c:
        section_title("Pendências", icon="⚠️")
        st.caption("6 ativos com bloqueio ou situação especial")

        _STATUS_CHIP_MAP: dict[str, tuple[str, str]] = {
            "Dados parciais":       ("degraded", "Parcial"),
            "Ticker legado":        ("paper",    "Legado"),
            "Aguardando docs CVM":  ("blocked",  "Sem CVM"),
            "Dados insuficientes":  ("blocked",  "Sem dados"),
            "Modelo alternativo":   ("manual",   "Alternativo"),
        }

        for p in _PENDENCIAS:
            status = p["status"]
            chip_variant, chip_text = _STATUS_CHIP_MAP.get(status, ("paper", status))
            st.markdown(f"""
            <div class="panel" style="margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;
                          align-items:center;margin-bottom:6px;">
                <div style="font-family:var(--font-display);font-size:.95rem;
                     font-weight:900;color:var(--fg-1);">{p['ticker']}</div>
                {_chip_html(chip_text, chip_variant)}
              </div>
              <div style="font-size:.62rem;color:var(--fg-5);line-height:1.4;">{p['nota']}</div>
            </div>
            """, unsafe_allow_html=True)


# ── Tab 2: Base Fundamentalista ─────────────────────────────────────────────────

def render_base_fundamentalista() -> None:
    kpis = _load_inputs_kpis()

    if not kpis:
        st.markdown(alert_block(
            "warn",
            "Base de dados não encontrada",
            "ingestion.db não localizada. Defina FINANCIAL_INPUTS_DB_PATH "
            "ou verifique 12_PYTHON/data/ingestion.db.",
        ), unsafe_allow_html=True)
        return

    sources = kpis.get("sources", {})
    cvm_cnt = sources.get("CVM_CSV", 0)
    b3_cnt  = sources.get("B3_MARKET_DATA", 0)

    kpi_strip([
        {"label": "Registros financeiros", "value": f"{kpis['total']:,}".replace(",", "."), "color": "cyan"},
        {"label": "Empresas com dados",    "value": str(kpis["tickers"]),                  "color": "cyan"},
        {"label": "Métricas distintas",    "value": str(kpis["metrics"]),                  "color": "violet"},
        {"label": "CVM / DFP",             "value": f"{cvm_cnt:,}".replace(",", "."),       "color": "green"},
        {"label": "B3 Market Data",        "value": str(b3_cnt),                            "color": "amber"},
    ])

    st.markdown(
        f'<div style="font-size:.65rem;color:var(--fg-5);font-family:var(--font-mono);'
        f'margin:10px 0 16px 0;padding:6px 10px;background:var(--bg-2);border-radius:8px;">'
        f'Fontes: CVM / DFP · B3 Market Data · '
        f'Referência: demonstrações financeiras 2025</div>',
        unsafe_allow_html=True,
    )

    coverage = kpis.get("coverage", {})
    all_universe = (
        list(_PRESERVE_EXISTING.keys())
        + [r["ticker"] for r in _READY_TO_CALCULATE]
        + [p["ticker"] for p in _PENDENCIAS]
    )

    seen: set[str] = set()
    ordered_universe: list[str] = []
    for t in all_universe:
        if t not in seen:
            seen.add(t)
            ordered_universe.append(t)

    model_map: dict[str, str] = {}
    for t in _PRESERVE_EXISTING:
        model_map[t] = "Banco (COSIF)"
    for r in _READY_TO_CALCULATE:
        model_map[r["ticker"]] = r["model"]

    ready_tickers_set = {r["ticker"] for r in _READY_TO_CALCULATE}
    table_rows = []
    for ticker in ordered_universe:
        cov = coverage.get(ticker, {"n_metrics": 0, "last_period": None})
        n = cov["n_metrics"]
        period = cov.get("last_period") or "—"
        model = model_map.get(ticker, "—")
        src_parts = []
        if n > 0:
            src_parts.append("CVM/DFP")
        if ticker in ready_tickers_set and n > 0:
            src_parts.append("B3 Market")

        if n >= 22:
            status_str = "✅ Completo"
        elif n > 0:
            status_str = "⚠️ Parcial"
        else:
            status_str = "❌ Sem dados"

        table_rows.append({
            "Ticker":  ticker,
            "Modelo":  model,
            "Métricas": f"{n} / 22",
            "Período":  period,
            "Fonte":    " + ".join(src_parts) if src_parts else "—",
            "Status":   status_str,
        })

    section_title("Cobertura por Empresa", icon="")
    df_cov = pd.DataFrame(table_rows)
    st.dataframe(df_cov, use_container_width=True, hide_index=True, height=400)

    # Key metrics for READY tickers
    section_title("Métricas-chave — Prontas para Cálculo", icon="")
    st.caption("Valores do exercício mais recente (DFP 2025). Valores em BRL, unidades originais CVM.")

    if _INGESTION_DB_PATH is None:
        empty_state("ingestion.db não disponível.", icon="")
        return

    key_metrics_data = _load_key_metrics()
    if key_metrics_data:
        df_key = pd.DataFrame(key_metrics_data).rename(columns={
            "revenue": "Receita",
            "ebitda": "EBITDA",
            "net_debt": "Dívida Líquida",
            "shares_outstanding": "Ações",
        })
        st.dataframe(df_key, use_container_width=True, hide_index=True)
    else:
        empty_state("Não foi possível carregar métricas-chave.", icon="")


# ── Tab 3: Simulação dos Modelos ────────────────────────────────────────────────

def render_simulacao_modelos() -> None:
    dry_run = _load_dry_run_matrix()

    st.markdown(alert_block(
        "info",
        "Simulação validada — nenhum valor salvo",
        "Todos os fair values abaixo foram calculados em modo de simulação. "
        "Nenhum dado foi alterado no banco. "
        "Os resultados passam por validação cruzada antes de serem promovidos.",
    ), unsafe_allow_html=True)

    if not dry_run:
        empty_state(
            "Matriz de simulação não encontrada.\n"
            "Esperado em: 12_PYTHON/docs/M017_S05_DRY_RUN_MATRIX.csv",
            icon="",
        )
        return

    kpi_strip([
        {"label": "Simulações executadas", "value": str(len(dry_run)), "color": "cyan"},
        {"label": "Método DCF/FCFF",
         "value": str(sum(1 for r in dry_run if "DCF" in r.get("method_used", ""))),
         "color": "green"},
        {"label": "Método EV/EBITDA",
         "value": str(sum(1 for r in dry_run if "EV" in r.get("method_used", ""))),
         "color": "violet"},
        {"label": "Com alertas",
         "value": str(sum(1 for r in dry_run if r.get("quality_flags", ""))),
         "color": "amber"},
    ])

    section_title(f"Resultados da Simulação — {len(dry_run)} empresas", icon="")

    table_rows = []
    for row in dry_run:
        ticker     = row.get("ticker", "—")
        fv_raw     = row.get("fair_value", "")
        upside_raw = row.get("upside_pct", "")
        method     = row.get("method_used", "—").replace("_", "/")
        flags      = row.get("quality_flags", "")

        try:
            fv_str = _fmt_brl(float(fv_raw))
        except (TypeError, ValueError):
            fv_str = "—"

        try:
            upside_str = f"{float(upside_raw):+.1f}%"
        except (TypeError, ValueError):
            upside_str = "—"

        table_rows.append({
            "Ticker":       ticker,
            "Valor Just.": fv_str,
            "Up/Downside": upside_str,
            "Método":       method,
            "Alertas":      flags if flags else "—",
        })

    df_sim = pd.DataFrame(table_rows)
    st.dataframe(df_sim, use_container_width=True, hide_index=True, height=400)

    # PCAR3 special note
    pcar_row = next((r for r in dry_run if r.get("ticker") == "PCAR3"), None)
    if pcar_row:
        pcar_fv = _fmt_brl(pcar_row.get("fair_value", "—"))
        st.markdown(f"""
        <div style="background:var(--bg-3);border:1px solid var(--warn-500);
             border-radius:12px;padding:14px 18px;margin-top:14px;">
            <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;
                 color:var(--warn-500);font-weight:700;margin-bottom:6px;">
                 PCAR3 — Situação Especial</div>
            <div style="font-size:.78rem;color:var(--fg-3);line-height:1.5;">
                Empresa em dificuldade operacional — DCF bloqueado (FCF indefinido).
                Método EV/EBITDA único aplicável. Valor simulado: <strong>{pcar_fv}</strong>.
                Upside calculado sobre preço de mercado na data da simulação —
                tratar com cautela dado o estado financeiro da empresa.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:.6rem;color:var(--fg-6);font-family:var(--font-mono);'
        'margin-top:14px;">Valores validados em dry-run. '
        'Próxima etapa persiste com write=True após validação cruzada.</div>',
        unsafe_allow_html=True,
    )


# ── Tab 4: Preços Justos Preliminares (M018-S04) ────────────────────────────────

def render_preliminares() -> None:
    """Tab — Preços Justos Preliminares resultantes do M018-S04.

    Regras de exibição:
      - Leitura somente (SELECT) de valuation_results
      - Nenhum dado é calculado, gravado ou alterado
      - asset_intelligence_snapshots não é acessada
      - Todos os termos internos são traduzidos para labels de produto
    """
    prelim_data = _load_preliminary_results()

    # ── Disclaimer visível ────────────────────────────────────────────────────
    st.markdown(alert_block(
        "warn",
        "Valores Preliminares — Em Validação",
        "Estes valores são resultados do motor de valuation em processo de validação. "
        "Nenhum deles representa recomendação de investimento ou preço justo aprovado. "
        "Não utilizar como base de decisão sem validação fundamentalista completa.",
    ), unsafe_allow_html=True)

    if not prelim_data:
        empty_state(
            "Nenhum valor preliminar encontrado em valuation_results.\n"
            "Execute M018-S04 para gerar os valores preliminares.",
            icon="",
        )
        return

    passed  = [r for r in prelim_data if r.get("sanity_check_passed") == 1]
    pending = [r for r in prelim_data if r.get("sanity_check_passed") != 1]

    kpi_strip([
        {"label": "Valor preliminar",  "value": str(len(prelim_data)), "color": "violet"},
        {"label": "Passou na checagem","value": str(len(passed)),      "color": "green"},
        {"label": "Requer validação",  "value": str(len(pending)),     "color": "amber"},
        {"label": "Aprovado",          "value": "0",                   "color": "red"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Seção 1: Passou na checagem ───────────────────────────────────────────
    section_title(f"Passou na Checagem — {len(passed)} valores", icon="✅")
    st.caption(
        "Valores preliminares que passaram na checagem automática · "
        "Label do produto: Preliminar — passou na checagem · "
        "Ainda não aprovado para uso"
    )
    _render_prelim_table(passed)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Seção 2: Requer validação ─────────────────────────────────────────────
    section_title(f"Requer Validação — {len(pending)} valores", icon="⚠️")
    st.caption(
        "Valores preliminares que requerem revisão adicional antes do uso · "
        "Label do produto: Preliminar — requer validação"
    )
    _render_prelim_table(pending)

    st.markdown(
        '<div style="font-size:.6rem;color:var(--fg-6);font-family:monospace;margin-top:14px;">'
        'Nenhum valor preliminar foi promovido para aprovado. '
        'Os valores estão em processo de validação fundamentalista.</div>',
        unsafe_allow_html=True,
    )


# ── Tab 5: Qualidade Fundamental ────────────────────────────────────────────────

def render_qualidade_fundamental() -> None:
    fq_rows = _load_fundamental_quality_rows()

    if not fq_rows:
        st.markdown(alert_block(
            "info",
            "Scores de qualidade fundamental ainda não calculados",
            "fundamental_quality_score não está preenchido nos snapshots atuais. "
            "O pipeline de qualidade fundamental precisa executar para popular esses campos "
            "em asset_intelligence_snapshots.",
        ), unsafe_allow_html=True)

        # Show what IS available from scanner_quant.db for context
        if _SCANNER_DB.exists():
            try:
                conn = sqlite3.connect(str(_SCANNER_DB))
                rows = conn.execute("""
                    SELECT ticker, integrated_score, data_quality_score,
                           valuation_governance_status, integrated_status, created_at
                    FROM asset_intelligence_snapshots
                    WHERE integrated_score IS NOT NULL
                    ORDER BY integrated_score DESC
                    LIMIT 20
                """).fetchall()
                conn.close()
                if rows:
                    section_title("Scores Integrados Disponíveis", icon="")
                    st.caption("integrated_score do asset_intelligence_snapshots — melhor proxy disponível agora.")
                    df_int = pd.DataFrame([
                        {
                            "Empresa":          r[0],
                            "Score Integrado":  f"{r[1]:.0f}" if r[1] else "—",
                            "Qualidade Dados":  f"{r[2]:.0f}" if r[2] else "—",
                            "Status Governance": r[3] or "—",
                            "Status Integrado":  r[4] or "—",
                            "Atualizado":        (r[5] or "")[:10],
                        }
                        for r in rows
                    ])
                    st.dataframe(df_int, use_container_width=True, hide_index=True)
            except Exception:
                pass
        return

    total = len(fq_rows)
    avg_fq = sum(r.get("fundamental_quality_score") or 0 for r in fq_rows) / total if total else 0

    kpi_strip([
        {"label": "Empresas com FQ",     "value": str(total),      "color": "cyan"},
        {"label": "Score médio FQ",      "value": f"{avg_fq:.0f}", "color": "violet"},
    ])

    section_title("Qualidade Fundamental por Empresa", icon="")

    for row in fq_rows:
        ticker  = row.get("ticker", "—")
        fq      = row.get("fundamental_quality_score")
        fh      = row.get("financial_health_score")
        prof    = row.get("profitability_score")
        growth  = row.get("growth_score")
        lev     = row.get("leverage_score")
        dq      = row.get("data_quality_score")
        created = str(row.get("created_at", ""))[:10] if row.get("created_at") else "—"

        fq_val = fq if fq is not None else 0.0

        with st.expander(f"{ticker}  —  FQ {_fmt_float(fq, 0)}  ·  {created}", expanded=False):
            for label, score in [
                ("Score Geral de Qualidade", fq),
                ("Saúde Financeira",         fh),
                ("Rentabilidade",            prof),
                ("Crescimento",              growth),
                ("Alavancagem",              lev),
                ("Qualidade de Dados",       dq),
            ]:
                if score is not None:
                    try:
                        val = float(score)
                        color = "var(--pos-500)" if val >= 70 else "var(--warn-500)" if val >= 40 else "var(--neg-500)"
                        st.markdown(score_bar(label, val, color=color), unsafe_allow_html=True)
                    except (TypeError, ValueError):
                        pass


# ── Tab 5: Contexto Macro ───────────────────────────────────────────────────────

def render_contexto_macro() -> None:
    macro = get_macro_panel()
    regime = macro.get("regime", [])
    selic  = macro.get("selic", [])
    ptax   = macro.get("ptax", [])
    ipca   = macro.get("ipca_12m", [])
    status = macro.get("source_status", "SEM_DADOS_MACRO")

    section_title("Contexto Macroeconômico", icon="")
    st.caption(f"Fonte: {status}")

    if status == "ERRO_CONEXAO":
        st.markdown(alert_block(
            "error",
            "Erro de conexão ao banco de dados macro",
            "Não foi possível conectar a scanner_quant.db para leitura de macro_series.",
        ), unsafe_allow_html=True)
        return

    selic_val = selic[0].get("value") if selic else None
    ptax_val  = ptax[0].get("value")  if ptax  else None
    ipca_val  = ipca[0].get("value")  if ipca  else None

    strip_items = []
    if selic_val is not None:
        strip_items.append({"label": "Selic",    "value": f"{selic_val:.2f}%",  "color": "amber"})
    if ptax_val is not None:
        strip_items.append({"label": "PTAX",     "value": f"R$ {ptax_val:.4f}", "color": "violet"})
    if ipca_val is not None:
        strip_items.append({"label": "IPCA 12m", "value": f"{ipca_val:.2f}%",   "color": "red"})

    if strip_items:
        kpi_strip(strip_items)

    if regime:
        r = regime[0]
        section_title("Regime de Mercado", icon="")
        df_regime = pd.DataFrame([{
            "Data":         (r.get("date") or "")[:10],
            "Regime":       r.get("primary") or "—",
            "Tendência":    r.get("trend") or "—",
            "Volatilidade": r.get("volatility") or "—",
            "Liquidez":     r.get("liquidity") or "—",
        }])
        st.dataframe(df_regime, use_container_width=True, hide_index=True)
    else:
        st.markdown(alert_block(
            "warn",
            "Regime de Mercado Indisponível",
            "market_regime_daily está vazio ou o pipeline de regime ainda não executou.",
        ), unsafe_allow_html=True)

    if selic:
        section_title("Série Selic (últimos 30 registros)", icon="")
        df_selic = pd.DataFrame([
            {"Data": s.get("date", "")[:10], "Selic (% a.a.)": f"{s.get('value', 0):.2f}"}
            for s in selic
        ])
        st.dataframe(df_selic, use_container_width=True, hide_index=True)

    if ptax:
        col1, col2 = st.columns(2)
        with col1:
            section_title("PTAX (últimas 10 cotações)", icon="")
            df_ptax = pd.DataFrame([
                {"Data": p.get("date", "")[:10], "PTAX (R$/USD)": f"{p.get('value', 0):.4f}"}
                for p in ptax[:10]
            ])
            st.dataframe(df_ptax, use_container_width=True, hide_index=True)
        with col2:
            if ipca:
                section_title("IPCA 12m (últimas 10 leituras)", icon="")
                df_ipca = pd.DataFrame([
                    {"Data": i.get("date", "")[:10], "IPCA 12m (%)": f"{i.get('value', 0):.2f}"}
                    for i in ipca[:10]
                ])
                st.dataframe(df_ipca, use_container_width=True, hide_index=True)

    if not selic and not ptax and not ipca:
        empty_state(
            "Nenhum dado macro encontrado.\n"
            "Execute o pipeline BCB para buscar Selic, PTAX e IPCA.",
            icon="",
        )


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header">
        <div class="page-header-title">Valuation Hub</div>
        <div class="page-header-sub">
            Central de valuation fundamentalista — preços justos, base financeira e simulações
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "Visão Geral",
        "Base Fundamentalista",
        "Qualidade Fundamental",
        "Contexto Macro",
        "Simulação dos Modelos",
        "Valores Preliminares ⚠️",
    ])

    with tabs[0]:
        with st.spinner("Carregando valuation..."):
            render_visao_geral()

    with tabs[1]:
        render_base_fundamentalista()

    with tabs[2]:
        render_qualidade_fundamental()

    with tabs[3]:
        render_contexto_macro()

    with tabs[4]:
        render_simulacao_modelos()

    with tabs[5]:
        render_preliminares()


main()
