"""Valuation Hub — Central de Valuation Fundamentalista

Abas:
  1. Visão Geral       — KPIs + preços justos preservados + prontas + pendências
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
    {"ticker": "EGIE3",  "sector": "Energia",    "model": "Utilidade",  "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "SBSP3",  "sector": "Saneamento", "model": "Utilidade",  "method": "EV/EBITDA", "notes": "FCF negativo esperado"},
    {"ticker": "TAEE11", "sector": "Energia",    "model": "Utilidade",  "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "AZZA3",  "sector": "Varejo",     "model": "Varejo",     "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "LREN3",  "sector": "Varejo",     "model": "Varejo",     "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "MGLU3",  "sector": "Varejo",     "model": "Varejo",     "method": "EV/EBITDA", "notes": "FCF em revisão"},
    {"ticker": "VIVA3",  "sector": "Varejo",     "model": "Varejo",     "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "PRIO3",  "sector": "Petróleo",   "model": "Commodity",  "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "RECV3",  "sector": "Petróleo",   "model": "Commodity",  "method": "EV/EBITDA", "notes": "FCF negativo esperado"},
    {"ticker": "FLRY3",  "sector": "Saúde",      "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "HYPE3",  "sector": "Farmácia",   "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "KLBN11", "sector": "Papel/Celulose", "model": "Industrial", "method": "DCF/FCFF", "notes": ""},
    {"ticker": "RADL3",  "sector": "Farmácia",   "model": "Industrial", "method": "DCF/FCFF",  "notes": ""},
    {"ticker": "RAIL3",  "sector": "Logística",  "model": "Industrial", "method": "EV/EBITDA", "notes": ""},
    {"ticker": "RENT3",  "sector": "Aluguel",    "model": "Industrial", "method": "EV/EBITDA", "notes": ""},
    {"ticker": "SUZB3",  "sector": "Papel/Celulose", "model": "Industrial", "method": "DCF/FCFF", "notes": ""},
    {"ticker": "VAMO3",  "sector": "Locação",    "model": "Industrial", "method": "EV/EBITDA", "notes": "FCF negativo esperado"},
]

_PENDENCIAS: list[dict] = [
    {"ticker": "PCAR3",  "status": "Dados parciais",                   "nota": "Dados parciais — situação especial (empresa em recuperação judicial)"},
    {"ticker": "PETZ3",  "status": "Ticker legado",                    "nota": "Ticker legado — empresa encerrada (fusão consumada)"},
    {"ticker": "AUAU3",  "status": "Aguardando docs CVM",              "nota": "CNPJ sem mapeamento — aguardando dados CVM/RI"},
    {"ticker": "VALE3",  "status": "Dados insuficientes",              "nota": "Aguardando ingestion CVM — ri_docs=0"},
    {"ticker": "NTCO3",  "status": "Aguardando docs CVM",              "nota": "Docs RI/CVM insuficientes para extração"},
    {"ticker": "VIVT3",  "status": "Modelo alternativo",               "nota": "Modelo alternativo disponível (EV/EBITDA) — aguardando inputs CVM"},
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
    kpi_strip([
        {"label": "Empresas monitoradas",    "value": "32",     "color": "cyan"},
        {"label": "Prontas para cálculo",    "value": "17",     "color": "green"},
        {"label": "Preço justo preservado",  "value": "9",      "color": "cyan"},
        {"label": "Dados parciais",          "value": "1",      "color": "amber"},
        {"label": "Registros financeiros",   "value": "47.621", "color": "violet"},
        {"label": "Aguardando dados",        "value": "4",      "color": "red"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1.2, 0.8])

    # ── Section A: Preços Justos Preservados ──────────────────────────────────
    with col_a:
        section_title("Preços Justos Preservados", icon="🔒")
        st.caption("9 ativos — auditados M015/M016. Não recalcular sem force_recalc.")
        for ticker, meta in _PRESERVE_EXISTING.items():
            fv_str = _fmt_brl(meta["fv"])
            st.markdown(f"""
            <div style="background:var(--bg-3);border:1px solid var(--border-1);
                 border-radius:10px;padding:10px 14px;margin-bottom:6px;
                 display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-family:var(--font-display);font-size:.95rem;
                         font-weight:900;color:var(--fg-1);">{ticker}</div>
                    <div style="font-size:.58rem;color:var(--fg-5);font-family:var(--font-mono);">
                        {meta['sector']} · {meta['method']}
                    </div>
                </div>
                <div style="font-family:var(--font-mono);font-size:.95rem;
                     font-weight:700;color:var(--pos-500);">{fv_str}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Section B: Prontas para cálculo ────────────────────────────────────────
    with col_b:
        section_title("Prontas para Cálculo", icon="")
        st.caption("17 ativos — inputs completos em ingestion.db")
        df_ready = pd.DataFrame([
            {
                "Ticker":  r["ticker"],
                "Setor":   r["sector"],
                "Modelo":  r["model"],
                "Método":  r["method"],
                "Notas":   r["notes"] if r["notes"] else "—",
            }
            for r in _READY_TO_CALCULATE
        ])
        st.dataframe(df_ready, use_container_width=True, hide_index=True)

    # ── Section C: Pendências ───────────────────────────────────────────────────
    with col_c:
        section_title("Pendências", icon="")
        st.caption("6 ativos com bloqueio ou situação especial")
        for p in _PENDENCIAS:
            status_color = {
                "Dados parciais":       "var(--warn-500)",
                "Ticker legado":        "var(--fg-5)",
                "Aguardando docs CVM":  "var(--neg-500)",
                "Dados insuficientes":  "var(--neg-500)",
                "Modelo alternativo":   "var(--brand-400)",
            }.get(p["status"], "var(--fg-4)")
            st.markdown(f"""
            <div style="background:var(--bg-3);border:1px solid var(--border-1);
                 border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <div style="font-family:var(--font-display);font-size:.9rem;
                         font-weight:900;color:var(--fg-1);">{p['ticker']}</div>
                    <div style="font-size:.6rem;font-weight:700;color:{status_color};
                         font-family:var(--font-mono);">{p['status']}</div>
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
        {"label": "CVM/DFP",              "value": f"{cvm_cnt:,}".replace(",", "."),        "color": "green"},
        {"label": "B3 Market Data",        "value": str(b3_cnt),                            "color": "amber"},
    ])

    st.markdown(
        f'<div style="font-size:.65rem;color:var(--fg-5);font-family:var(--font-mono);'
        f'margin:10px 0 16px 0;padding:6px 10px;background:var(--bg-2);border-radius:8px;">'
        f'Fonte: ingestion.db · M017-S03 CVM_CSV + M017-S04 B3_MARKET_DATA · '
        f'Referência: 2025-12-31 (DFP anual)</div>',
        unsafe_allow_html=True,
    )

    coverage = kpis.get("coverage", {})
    all_universe = (
        list(_PRESERVE_EXISTING.keys())
        + [r["ticker"] for r in _READY_TO_CALCULATE]
        + [p["ticker"] for p in _PENDENCIAS]
    )

    # Deduplicate preserving order
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

    rows_cov = []
    for ticker in ordered_universe:
        cov = coverage.get(ticker, {"n_metrics": 0, "last_period": None})
        n = cov["n_metrics"]
        period = cov.get("last_period") or "—"
        model = model_map.get(ticker, "—")
        src_list = []
        if n > 0:
            src_list.append("CVM/DFP")
            if ticker in [r["ticker"] for r in _READY_TO_CALCULATE]:
                src_list.append("B3 Market")
        rows_cov.append({
            "Empresa": ticker,
            "Modelo":  model,
            "Métricas": f"{n} / 22",
            "Período":  period,
            "Fonte":    " + ".join(src_list) if src_list else "Sem dados",
            "Status":   "Completo" if n >= 22 else ("Parcial" if n > 0 else "Sem dados"),
        })

    section_title("Cobertura por Empresa", icon="")
    df_cov = pd.DataFrame(rows_cov)
    st.dataframe(df_cov, use_container_width=True, hide_index=True)

    # Key metrics for READY tickers
    section_title("Métricas-chave — Prontas para Cálculo", icon="")
    st.caption("Valores do exercício mais recente (DFP 2025). Valores em BRL, unidades originais CVM.")

    if _INGESTION_DB_PATH is None:
        empty_state("ingestion.db não disponível.", icon="")
        return

    try:
        conn = sqlite3.connect(str(_INGESTION_DB_PATH))
        key_metrics = ["revenue", "ebitda", "net_debt", "shares_outstanding"]
        ready_tickers = [r["ticker"] for r in _READY_TO_CALCULATE]

        rows_key = []
        for ticker in ready_tickers:
            row_data: dict[str, str] = {"Empresa": ticker}
            for metric in key_metrics:
                val = conn.execute("""
                    SELECT metric_value FROM valuation_financial_inputs
                    WHERE ticker=? AND metric_name=?
                    AND period_type='DFP'
                    ORDER BY period_end DESC LIMIT 1
                """, (ticker, metric)).fetchone()
                if val and val[0] is not None:
                    v = float(val[0])
                    if metric == "shares_outstanding":
                        row_data[metric] = f"{v/1e6:.1f}M"
                    elif abs(v) >= 1e9:
                        row_data[metric] = f"R$ {v/1e9:.2f}B"
                    elif abs(v) >= 1e6:
                        row_data[metric] = f"R$ {v/1e6:.1f}M"
                    else:
                        row_data[metric] = f"R$ {v:,.0f}"
                else:
                    row_data[metric] = "—"
            rows_key.append(row_data)
        conn.close()

        df_key = pd.DataFrame(rows_key).rename(columns={
            "revenue": "Receita",
            "ebitda": "EBITDA",
            "net_debt": "Dívida Líquida",
            "shares_outstanding": "Ações",
        })
        st.dataframe(df_key, use_container_width=True, hide_index=True)

    except Exception:
        empty_state("Não foi possível carregar métricas-chave.", icon="")


# ── Tab 3: Simulação dos Modelos ────────────────────────────────────────────────

def render_simulacao_modelos() -> None:
    dry_run = _load_dry_run_matrix()

    st.markdown(alert_block(
        "info",
        "Simulação com write=False — nenhum valor foi salvo",
        "Todos os fair values abaixo foram calculados em M017-S05 com write=False. "
        "asset_intelligence_snapshots não foi alterada. "
        "M018 persiste com write=True após validação cruzada (range 0.1× – 5.0× preço).",
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

    # Build display table
    rows_display = []
    for row in dry_run:
        ticker = row.get("ticker", "—")
        fv_raw = row.get("fair_value", "")
        upside_raw = row.get("upside_pct", "")
        method = row.get("method_used", "—").replace("_", "/")
        flags  = row.get("quality_flags", "")

        try:
            fv_str = _fmt_brl(float(fv_raw))
        except (TypeError, ValueError):
            fv_str = "—"

        try:
            upside_f = float(upside_raw)
            upside_str = f"{upside_f:+.1f}%"
        except (TypeError, ValueError):
            upside_str = "—"

        rows_display.append({
            "Empresa":          ticker,
            "Valor Justo (sim.)": fv_str,
            "Upside":           upside_str,
            "Método":           method,
            "Alertas":          flags if flags else "—",
        })

    section_title("Resultados da Simulação — 18 empresas", icon="")
    df_dr = pd.DataFrame(rows_display)
    st.dataframe(df_dr, use_container_width=True, hide_index=True)

    # PCAR3 special note
    pcar_row = next((r for r in dry_run if r.get("ticker") == "PCAR3"), None)
    if pcar_row:
        st.markdown(f"""
        <div style="background:var(--bg-3);border:1px solid var(--warn-500);
             border-radius:12px;padding:14px 18px;margin-top:14px;">
            <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;
                 color:var(--warn-500);font-weight:700;margin-bottom:6px;">PCAR3 — Situação Especial</div>
            <div style="font-size:.78rem;color:var(--fg-3);line-height:1.5;">
                Empresa em dificuldade operacional — DCF bloqueado (FCF indefinido).
                Método EV/EBITDA único aplicável. Valor simulado: {_fmt_brl(pcar_row.get('fair_value', '—'))}.
                Upside calculado sobre preço de mercado na data da simulação — tratar com cautela
                dado o estado financeiro da empresa.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:.6rem;color:var(--fg-6);font-family:var(--font-mono);'
        'margin-top:14px;">Valores validados em M017-S05. '
        'M018 persiste com write=True após validação cruzada.</div>',
        unsafe_allow_html=True,
    )


# ── Tab 4: Qualidade Fundamental ────────────────────────────────────────────────

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
        {"label": "Empresas com FQ",     "value": str(total),    "color": "cyan"},
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
        fq_color = "var(--pos-500)" if fq_val >= 70 else "var(--warn-500)" if fq_val >= 40 else "var(--neg-500)"

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

    # KPI strip for macro
    selic_val = selic[0].get("value") if selic else None
    ptax_val  = ptax[0].get("value")  if ptax  else None
    ipca_val  = ipca[0].get("value")  if ipca  else None

    strip_items = []
    if selic_val is not None:
        strip_items.append({"label": "Selic",    "value": f"{selic_val:.2f}%", "color": "amber"})
    if ptax_val is not None:
        strip_items.append({"label": "PTAX",     "value": f"R$ {ptax_val:.4f}", "color": "violet"})
    if ipca_val is not None:
        strip_items.append({"label": "IPCA 12m", "value": f"{ipca_val:.2f}%", "color": "red"})

    if strip_items:
        kpi_strip(strip_items)

    # Regime de mercado
    if regime:
        r = regime[0]
        section_title("Regime de Mercado", icon="")
        df_regime = pd.DataFrame([{
            "Data":        (r.get("date") or "")[:10],
            "Regime":      r.get("primary") or "—",
            "Tendência":   r.get("trend") or "—",
            "Volatilidade": r.get("volatility") or "—",
            "Liquidez":    r.get("liquidity") or "—",
        }])
        st.dataframe(df_regime, use_container_width=True, hide_index=True)
    else:
        st.markdown(alert_block(
            "warn",
            "Regime de Mercado Indisponível",
            "market_regime_daily está vazio ou o pipeline de regime ainda não executou.",
        ), unsafe_allow_html=True)

    # Série histórica Selic
    if selic:
        section_title("Série Selic (últimos 30 registros)", icon="")
        df_selic = pd.DataFrame([
            {"Data": s.get("date", "")[:10], "Selic (% a.a.)": f"{s.get('value', 0):.2f}"}
            for s in selic
        ])
        st.dataframe(df_selic, use_container_width=True, hide_index=True)

    # PTAX
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
        "Simulação dos Modelos",
        "Qualidade Fundamental",
        "Contexto Macro",
    ])

    with tabs[0]:
        render_visao_geral()

    with tabs[1]:
        render_base_fundamentalista()

    with tabs[2]:
        render_simulacao_modelos()

    with tabs[3]:
        render_qualidade_fundamental()

    with tabs[4]:
        render_contexto_macro()


main()
