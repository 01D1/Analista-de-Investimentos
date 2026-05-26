"""Cobertura de Valuation — Universo M017

Abas:
  1. Universo de Cobertura    — 32 tickers com status em português
  2. Simulação dos Modelos    — dry-run M017-S05 (write=False)
  3. Cobertura CVM/DFP        — valuation_financial_inputs por ticker
  4. Preços Justos            — 9 fair values auditados M015/M016

Regras:
  - Nenhum cálculo de fair_value
  - Nenhuma escrita no banco
  - Sem JSON bruto exibido ao usuário
  - Status em português produto
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st

from src.ui.components import section_title, kpi_strip, empty_state, alert_block

# ── DB Paths ───────────────────────────────────────────────────────────────────
_SCANNER_DB   = _ROOT / "data" / "database" / "scanner_quant.db"
_DRY_RUN_MATRIX = _ROOT.parent / "12_PYTHON" / "docs" / "M017_S05_DRY_RUN_MATRIX.csv"


def _resolve_ingestion_db() -> Path | None:
    import os
    env = os.environ.get("FINANCIAL_INPUTS_DB_PATH")
    if env:
        p = Path(env)
        if p.exists():
            return p
    candidate = _ROOT.parent / "12_PYTHON" / "data" / "ingestion.db"
    if candidate.exists():
        return candidate
    fallback = _ROOT / "data" / "ingestion.db"
    if fallback.exists():
        return fallback
    return None


_INGESTION_DB = _resolve_ingestion_db()

# ── M017 Universe ──────────────────────────────────────────────────────────────
# (ticker, model_status, sector_model, method_suggested, block_reason, quality_flags)
_UNIVERSE = [
    ("ABCB4",  "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("BBAS3",  "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("BBDC4",  "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("BPAC11", "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("BRSR6",  "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("ITUB4",  "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("SANB11", "PRESERVE_EXISTING",   "Banco",       "P/BV",      "",                               ""),
    ("PETR4",  "PRESERVE_EXISTING",   "Commodity",   "DCF/FCFF",  "",                               ""),
    ("WEGE3",  "PRESERVE_EXISTING",   "Industrial",  "DCF/FCFF",  "",                               ""),
    ("EGIE3",  "READY_TO_CALCULATE",  "Utilidade",   "DCF/FCFF",  "",                               ""),
    ("SBSP3",  "READY_TO_CALCULATE",  "Utilidade",   "EV/EBITDA", "",                               "FCF negativo esperado"),
    ("TAEE11", "READY_TO_CALCULATE",  "Utilidade",   "DCF/FCFF",  "",                               ""),
    ("AZZA3",  "READY_TO_CALCULATE",  "Varejo",      "DCF/FCFF",  "",                               ""),
    ("LREN3",  "READY_TO_CALCULATE",  "Varejo",      "DCF/FCFF",  "",                               ""),
    ("MGLU3",  "READY_TO_CALCULATE",  "Varejo",      "EV/EBITDA", "",                               "FCF em revisão"),
    ("VIVA3",  "READY_TO_CALCULATE",  "Varejo",      "DCF/FCFF",  "",                               ""),
    ("PRIO3",  "READY_TO_CALCULATE",  "Commodity",   "DCF/FCFF",  "",                               ""),
    ("RECV3",  "READY_TO_CALCULATE",  "Commodity",   "EV/EBITDA", "",                               "FCF negativo esperado"),
    ("FLRY3",  "READY_TO_CALCULATE",  "Industrial",  "DCF/FCFF",  "",                               ""),
    ("HYPE3",  "READY_TO_CALCULATE",  "Industrial",  "DCF/FCFF",  "",                               ""),
    ("KLBN11", "READY_TO_CALCULATE",  "Industrial",  "DCF/FCFF",  "",                               ""),
    ("RADL3",  "READY_TO_CALCULATE",  "Industrial",  "DCF/FCFF",  "",                               ""),
    ("RAIL3",  "READY_TO_CALCULATE",  "Industrial",  "EV/EBITDA", "",                               ""),
    ("RENT3",  "READY_TO_CALCULATE",  "Industrial",  "EV/EBITDA", "",                               ""),
    ("SUZB3",  "READY_TO_CALCULATE",  "Industrial",  "DCF/FCFF",  "",                               ""),
    ("VAMO3",  "READY_TO_CALCULATE",  "Industrial",  "EV/EBITDA", "",                               "FCF negativo esperado"),
    ("PCAR3",  "PARTIAL_INPUTS",      "Varejo",      "EV/EBITDA", "Empresa em recuperação judicial","Distressed"),
    ("VIVT3",  "TECH_FALLBACK",       "Industrial",  "EV/EBITDA", "Inputs CVM pendentes",           ""),
    ("VALE3",  "NEEDS_DATA",          "Commodity",   "DCF/FCFF",  "ri_docs=0",                      ""),
    ("AUAU3",  "NEEDS_RI_DOCS",       "—",           "—",         "CNPJ nulo — sem dados CVM",      ""),
    ("NTCO3",  "NEEDS_RI_DOCS",       "Varejo",      "DCF/FCFF",  "Docs RI insuficientes",          ""),
    ("PETZ3",  "LEGACY_TICKER",       "Varejo",      "—",         "Encerrada — fusão consumada",    ""),
]

_PRESERVE_FV = {
    "ABCB4":  210.50, "BBAS3":  64.84, "BBDC4":  34.63,
    "BPAC11":   8.46, "BRSR6":   4.66, "ITUB4":  73.69,
    "SANB11":  86.79, "PETR4":  81.12, "WEGE3":  40.16,
}

_STATUS_PT: dict[str, str] = {
    "PRESERVE_EXISTING":  "Preço justo preservado",
    "READY_TO_CALCULATE": "Pronta para cálculo",
    "PARTIAL_INPUTS":     "Dados parciais",
    "TECH_FALLBACK":      "Modelo alternativo",
    "NEEDS_DATA":         "Dados insuficientes",
    "NEEDS_RI_DOCS":      "Aguardando docs CVM",
    "LEGACY_TICKER":      "Ticker legado",
}

_STATUS_COLOR: dict[str, str] = {
    "PRESERVE_EXISTING":  "#22D3EE",
    "READY_TO_CALCULATE": "#4ADE80",
    "PARTIAL_INPUTS":     "#FBBF24",
    "TECH_FALLBACK":      "#FB923C",
    "NEEDS_DATA":         "#F87171",
    "NEEDS_RI_DOCS":      "#F87171",
    "LEGACY_TICKER":      "#64748B",
}

_STATUS_ORDER = [
    "PRESERVE_EXISTING", "READY_TO_CALCULATE", "PARTIAL_INPUTS",
    "TECH_FALLBACK", "NEEDS_DATA", "NEEDS_RI_DOCS", "LEGACY_TICKER",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def _load_ingestion_kpis() -> dict:
    if _INGESTION_DB is None:
        return {}
    try:
        conn = sqlite3.connect(str(_INGESTION_DB))
        total    = conn.execute("SELECT COUNT(*) FROM valuation_financial_inputs").fetchone()[0]
        tickers  = conn.execute("SELECT COUNT(DISTINCT ticker) FROM valuation_financial_inputs").fetchone()[0]
        metrics  = conn.execute("SELECT COUNT(DISTINCT metric_name) FROM valuation_financial_inputs").fetchone()[0]
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


def _load_dry_run_matrix() -> list[dict]:
    if not _DRY_RUN_MATRIX.exists():
        return []
    try:
        rows = []
        with open(_DRY_RUN_MATRIX, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
        return rows
    except Exception:
        return []


# ── Page render ────────────────────────────────────────────────────────────────

def main() -> None:
    kpis    = _load_ingestion_kpis()
    dry_run = _load_dry_run_matrix()
    dry_map = {r["ticker"]: r for r in dry_run}

    ready_cnt   = sum(1 for r in _UNIVERSE if r[1] == "READY_TO_CALCULATE")
    preserve_cnt = sum(1 for r in _UNIVERSE if r[1] == "PRESERVE_EXISTING")

    st.markdown("""
    <style>
    .cov-header {font-family:'Sora',sans-serif;font-weight:900;font-size:1.5rem;color:#F1F5F9;margin-bottom:4px}
    .cov-sub    {font-size:.75rem;color:#64748B;font-family:'JetBrains Mono',monospace;margin-bottom:18px}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="cov-header">Cobertura de Valuation</div>'
        '<div class="cov-sub">47.621 registros · 88 empresas CVM · 18 simulações (write=False) · '
        'Referência: 2025-12-31 · M017 FECHADO</div>',
        unsafe_allow_html=True,
    )

    # KPI strip
    total_kpi = f"{kpis.get('total', 0):,}".replace(",", ".") if kpis else "—"
    kpi_strip([
        {"label": "Base financeira",        "value": total_kpi,        "color": "cyan"},
        {"label": "Empresas CVM",           "value": str(kpis.get("tickers", "—")) if kpis else "—", "color": "cyan"},
        {"label": "Preço justo preservado", "value": str(preserve_cnt),"color": "green"},
        {"label": "Pronta para cálculo",    "value": str(ready_cnt),   "color": "cyan"},
        {"label": "Dados parciais",         "value": "1",              "color": "amber"},
        {"label": "Simulações OK",          "value": str(len(dry_run)),"color": "green"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Universo de Cobertura",
        "Simulação dos Modelos",
        "Cobertura CVM/DFP",
        "Preços Justos",
    ])

    # ── Tab 1: Universo de Cobertura ──────────────────────────────────────────
    with tab1:
        st.caption(f"{len(_UNIVERSE)} empresas com status de valuation definido — M017")

        status_groups: dict[str, list] = {}
        for row in _UNIVERSE:
            status_groups.setdefault(row[1], []).append(row)

        for status_key in _STATUS_ORDER:
            rows_in_group = status_groups.get(status_key, [])
            if not rows_in_group:
                continue
            color = _STATUS_COLOR.get(status_key, "#94A3B8")
            label_pt = _STATUS_PT.get(status_key, status_key)
            st.markdown(
                f'<div style="font-size:.7rem;font-weight:700;color:{color};'
                f'text-transform:uppercase;letter-spacing:.8px;margin:16px 0 6px 0;">'
                f'{label_pt} ({len(rows_in_group)})</div>',
                unsafe_allow_html=True,
            )

            rows_df = []
            for ticker, model_status, model, method, block, flags in rows_in_group:
                fv_str   = _fmt_brl(_PRESERVE_FV[ticker]) if ticker in _PRESERVE_FV else "—"
                dr       = dry_map.get(ticker)
                dr_fv    = _fmt_brl(dr["fair_value"]) if dr else "—"
                dr_up    = f"{float(dr['upside_pct']):+.1f}%" if (dr and dr.get("upside_pct")) else "—"
                rows_df.append({
                    "Empresa":         ticker,
                    "Modelo":          model,
                    "Método":          method,
                    "Preço Justo":     fv_str,
                    "Simulação FV":    dr_fv,
                    "Simulação Upside": dr_up,
                    "Bloqueio":        block if block else "—",
                    "Alertas":         flags if flags else "—",
                })

            df_group = pd.DataFrame(rows_df)
            st.dataframe(df_group, use_container_width=True, hide_index=True)

        st.markdown(
            '<div style="font-size:.58rem;color:#334155;font-family:monospace;margin-top:12px;">'
            'Preço Justo = auditado M015/M016 · Simulação = M017-S05 write=False</div>',
            unsafe_allow_html=True,
        )

    # ── Tab 2: Simulação dos Modelos ──────────────────────────────────────────
    with tab2:
        if not dry_run:
            st.warning("Matriz de simulação não encontrada: 12_PYTHON/docs/M017_S05_DRY_RUN_MATRIX.csv")
            return

        st.markdown(alert_block(
            "info",
            "Simulação com write=False — nenhum valor foi persistido",
            f"{len(dry_run)} empresas simuladas. "
            "asset_intelligence_snapshots não foi alterada. "
            "M018 persiste com write=True após validação cruzada (range 0.1× – 5.0× preço).",
        ), unsafe_allow_html=True)

        rows_dr = []
        for row in dry_run:
            ticker   = row.get("ticker", "—")
            fv_raw   = row.get("fair_value", "")
            upside   = row.get("upside_pct", "")
            method   = row.get("method_used", "—").replace("_", "/")
            conf_raw = row.get("confidence", "")
            flags    = row.get("quality_flags", "")

            try:
                fv_str = _fmt_brl(float(fv_raw))
            except (TypeError, ValueError):
                fv_str = "—"

            try:
                upside_f = float(upside)
                upside_str = f"{upside_f:+.1f}%"
            except (TypeError, ValueError):
                upside_str = "—"

            try:
                conf_str = f"{float(conf_raw):.0%}"
            except (TypeError, ValueError):
                conf_str = "—"

            rows_dr.append({
                "Empresa":           ticker,
                "Valor Justo (sim.)": fv_str,
                "Upside":            upside_str,
                "Método":            method,
                "Confiança":         conf_str,
                "Alertas":           flags if flags else "—",
            })

        df_dr = pd.DataFrame(rows_dr)
        st.dataframe(df_dr, use_container_width=True, hide_index=True)

        st.markdown(
            '<div style="font-size:.58rem;color:#475569;margin-top:10px;">'
            'Todos os valores acima são simulação (write=False). '
            'M018 persiste com write=True após validação cruzada (0.1× – 5.0× preço de mercado).</div>',
            unsafe_allow_html=True,
        )

    # ── Tab 3: Cobertura CVM/DFP ──────────────────────────────────────────────
    with tab3:
        if not kpis:
            st.warning(
                "ingestion.db não encontrada. "
                "Defina FINANCIAL_INPUTS_DB_PATH ou verifique 12_PYTHON/data/ingestion.db"
            )
            return

        sources  = kpis.get("sources", {})
        coverage = kpis.get("coverage", {})

        kpi_strip([
            {"label": "Total de registros",  "value": f"{kpis.get('total', 0):,}".replace(",", "."), "color": "cyan"},
            {"label": "Empresas com CVM/DFP", "value": str(kpis.get("tickers", "—")),                "color": "cyan"},
            {"label": "Métricas distintas",  "value": str(kpis.get("metrics", "—")),                 "color": "violet"},
        ])

        st.markdown("**Fontes de dados:**")
        for src, cnt in sources.items():
            st.markdown(f"- `{src}`: **{cnt:,}** registros")

        st.divider()
        section_title("Cobertura por Empresa (métricas extraídas)", icon="")

        rows_cov = []
        for ticker, _, model, _, _, _ in _UNIVERSE:
            cov = coverage.get(ticker, {"n_metrics": 0, "last_period": None})
            n   = cov["n_metrics"]
            period = cov.get("last_period") or "—"
            pct = f"{n / 22 * 100:.0f}%" if n else "0%"
            status_icon = "Completo" if n >= 22 else ("Parcial" if n > 0 else "Sem dados")
            rows_cov.append({
                "Empresa":    ticker,
                "Modelo":     model,
                "Métricas":   n,
                "Cobertura":  pct,
                "Período":    period,
                "Status":     status_icon,
            })

        df_cov = pd.DataFrame(rows_cov)
        st.dataframe(df_cov, use_container_width=True, hide_index=True)

        st.markdown("""
        <div style="font-size:.62rem;color:#475569;margin-top:8px;">
        22 métricas extraídas: revenue, ebit, ebitda, net_income, operating_cash_flow, capex,
        free_cash_flow, total_assets, cash_and_equivalents, short_term_debt, long_term_debt,
        gross_debt, net_debt, equity_book_value, shares_outstanding + 7 derivadas.
        Fonte: M017-S03 CVM_CSV + M017-S04 B3_MARKET_DATA.
        </div>
        """, unsafe_allow_html=True)

    # ── Tab 4: Preços Justos ──────────────────────────────────────────────────
    with tab4:
        st.caption(
            "9 preços justos auditados M015/M016 — não recalcular sem force_recalc=True explícito"
        )

        rows_fv = []
        for ticker, fv in _PRESERVE_FV.items():
            model_row = next((r for r in _UNIVERSE if r[0] == ticker), None)
            model  = model_row[2] if model_row else "—"
            method = model_row[3] if model_row else "—"
            rows_fv.append({
                "Empresa":   ticker,
                "Modelo":    model,
                "Método":    method,
                "Preço Justo": _fmt_brl(fv),
                "Status":    "Preço justo preservado",
                "Ação M018": "Manter — não recalcular sem force_recalc=True",
            })

        df_fv = pd.DataFrame(rows_fv)
        st.dataframe(df_fv, use_container_width=True, hide_index=True)

        st.info(
            "**PETZ3** — Ticker legado permanente — bloqueado.  \n"
            "**AUAU3** — CNPJ nulo / sem dados CVM — aguardando mapeamento.  \n"
            "**VALE3** — ri_docs=0 — aguarda ingestion CVM.  \n"
            "**PCAR3** — Dados parciais / Distressed — EV/EBITDA único aplicável em M018."
        )

        st.caption("M017 FECHADO 2026-05-26 · Próximo: M018 — Cálculo controlado com write=True")


main()
