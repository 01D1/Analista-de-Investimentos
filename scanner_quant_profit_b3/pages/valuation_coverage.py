"""
pages/valuation_coverage.py — Cobertura Valuation M017

Matriz de cobertura operacional pós-M017:
  - valuation_financial_inputs: 47.621 registros (ingestion.db)
  - 18 tickers dry-run OK (write=False) — M017-S05
  - 32 tickers com model_status definido
  - CVM/DFP/ITR coverage por ticker

Baseado em: M017-SUMMARY.md · M017-VALIDATION.md · M017_S05_DRY_RUN_MATRIX.csv
Milestone: M017 ✅ FECHADO (2026-05-26)
Regras:
  - Nenhum cálculo de fair_value
  - Nenhuma alteração de banco
  - Nenhuma chamada externa
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

# ── db paths ──────────────────────────────────────────────────────────────────
_SCANNER_DB  = _ROOT / "data" / "database" / "scanner_quant.db"
_INGESTION_DB: Path | None = None

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
_DRY_RUN_MATRIX = _ROOT.parent / "12_PYTHON" / "docs" / "M017_S05_DRY_RUN_MATRIX.csv"

# ── M017 Universe ─────────────────────────────────────────────────────────────
_UNIVERSE = [
    # ticker, model_status, sector_model, method_suggested, block_reason, quality_flags
    ("ABCB4",  "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("BBAS3",  "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("BBDC4",  "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("BPAC11", "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("BRSR6",  "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("ITUB4",  "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("SANB11", "PRESERVE_EXISTING",   "BANK",      "P/BV",      "",                        ""),
    ("PETR4",  "PRESERVE_EXISTING",   "COMMODITY", "DCF/FCFF",  "",                        ""),
    ("WEGE3",  "PRESERVE_EXISTING",   "INDUSTRY",  "DCF/FCFF",  "",                        ""),
    ("EGIE3",  "READY_TO_CALCULATE",  "UTILITY",   "DCF/FCFF",  "",                        ""),
    ("SBSP3",  "READY_TO_CALCULATE",  "UTILITY",   "EV/EBITDA", "",                        "FCF_NEGATIVE_EXPECTED"),
    ("TAEE11", "READY_TO_CALCULATE",  "UTILITY",   "DCF/FCFF",  "",                        ""),
    ("AZZA3",  "READY_TO_CALCULATE",  "RETAIL",    "DCF/FCFF",  "",                        ""),
    ("LREN3",  "READY_TO_CALCULATE",  "RETAIL",    "DCF/FCFF",  "",                        ""),
    ("MGLU3",  "READY_TO_CALCULATE",  "RETAIL",    "EV/EBITDA", "",                        "FCF_REVIEW"),
    ("VIVA3",  "READY_TO_CALCULATE",  "RETAIL",    "DCF/FCFF",  "",                        ""),
    ("PRIO3",  "READY_TO_CALCULATE",  "COMMODITY", "DCF/FCFF",  "",                        ""),
    ("RECV3",  "READY_TO_CALCULATE",  "COMMODITY", "EV/EBITDA", "",                        "FCF_NEGATIVE_EXPECTED"),
    ("FLRY3",  "READY_TO_CALCULATE",  "INDUSTRY",  "DCF/FCFF",  "",                        ""),
    ("HYPE3",  "READY_TO_CALCULATE",  "INDUSTRY",  "DCF/FCFF",  "",                        ""),
    ("KLBN11", "READY_TO_CALCULATE",  "INDUSTRY",  "DCF/FCFF",  "",                        ""),
    ("RADL3",  "READY_TO_CALCULATE",  "INDUSTRY",  "DCF/FCFF",  "",                        ""),
    ("RAIL3",  "READY_TO_CALCULATE",  "INDUSTRY",  "EV/EBITDA", "",                        ""),
    ("RENT3",  "READY_TO_CALCULATE",  "INDUSTRY",  "EV/EBITDA", "",                        ""),
    ("SUZB3",  "READY_TO_CALCULATE",  "INDUSTRY",  "DCF/FCFF",  "",                        ""),
    ("VAMO3",  "READY_TO_CALCULATE",  "INDUSTRY",  "EV/EBITDA", "",                        "FCF_NEGATIVE_EXPECTED"),
    ("PCAR3",  "PARTIAL_INPUTS",      "RETAIL",    "EV/EBITDA", "DISTRESSED",              "DISTRESSED"),
    ("VIVT3",  "TECH_FALLBACK",       "INDUSTRY",  "EV/EBITDA", "CVM inputs pendentes",    ""),
    ("VALE3",  "NEEDS_DATA",          "COMMODITY", "DCF/FCFF",  "ri_docs=0",               ""),
    ("AUAU3",  "NEEDS_RI_DOCS",       "—",         "—",         "CNPJ nulo / sem CVM",     ""),
    ("NTCO3",  "NEEDS_RI_DOCS",       "RETAIL",    "DCF/FCFF",  "ri_docs insuficientes",   ""),
    ("PETZ3",  "LEGACY_TICKER",       "RETAIL",    "—",         "Encerrado permanente",    ""),
]

_PRESERVE_FV = {
    "ABCB4": 210.50, "BBAS3": 64.84, "BBDC4": 34.63,
    "BPAC11": 8.46,  "BRSR6": 4.66,  "ITUB4": 73.69,
    "SANB11": 86.79, "PETR4": 81.12, "WEGE3": 40.16,
}

_STATUS_EMOJI = {
    "PRESERVE_EXISTING":  "🔒",
    "READY_TO_CALCULATE": "✅",
    "PARTIAL_INPUTS":     "🟡",
    "TECH_FALLBACK":      "🟠",
    "NEEDS_DATA":         "🔴",
    "NEEDS_RI_DOCS":      "🔴",
    "LEGACY_TICKER":      "⛔",
}

_STATUS_COLOR = {
    "PRESERVE_EXISTING":  "#22D3EE",
    "READY_TO_CALCULATE": "#4ADE80",
    "PARTIAL_INPUTS":     "#FBBF24",
    "TECH_FALLBACK":      "#FB923C",
    "NEEDS_DATA":         "#F87171",
    "NEEDS_RI_DOCS":      "#F87171",
    "LEGACY_TICKER":      "#64748B",
}


# ── helpers ───────────────────────────────────────────────────────────────────

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
            SELECT ticker, COUNT(DISTINCT metric_name) as n_metrics
            FROM valuation_financial_inputs
            GROUP BY ticker
            ORDER BY ticker
        """).fetchall()
        conn.close()
        return {
            "total": total, "tickers": tickers, "metrics": metrics,
            "sources": {r[0]: r[1] for r in src_rows},
            "coverage": {r[0]: r[1] for r in cov_rows},
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


# ── page render ───────────────────────────────────────────────────────────────

def main() -> None:
    kpis    = _load_ingestion_kpis()
    dry_run = _load_dry_run_matrix()
    dry_map = {r["ticker"]: r for r in dry_run}

    st.markdown("""
    <style>
    .cov-header {font-family:'Sora',sans-serif;font-weight:900;font-size:1.5rem;color:#F1F5F9;margin-bottom:4px}
    .cov-sub    {font-size:.75rem;color:#64748B;font-family:'JetBrains Mono',monospace;margin-bottom:18px}
    .cov-kpi    {background:#0F172A;border:1px solid #1E293B;border-radius:10px;padding:12px 16px;text-align:center}
    .cov-kpi-v  {font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:#22D3EE}
    .cov-kpi-l  {font-size:.6rem;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-top:4px}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="cov-header">📊 Cobertura Valuation — M017</div>'
        '<div class="cov-sub">47.621 registros · 88 tickers CVM · 18 dry-run OK (write=False) · '
        '2026-05-26 · Milestone M017 ✅ FECHADO</div>',
        unsafe_allow_html=True,
    )

    # ── KPI row ───────────────────────────────────────────────────────────
    total_kpi   = f"{kpis.get('total',0):,}"  if kpis else "—"
    tickers_kpi = str(kpis.get("tickers","—")) if kpis else "—"
    ready_cnt   = sum(1 for r in _UNIVERSE if r[1] == "READY_TO_CALCULATE")
    preserve_cnt = sum(1 for r in _UNIVERSE if r[1] == "PRESERVE_EXISTING")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, val, label in [
        (c1, total_kpi,        "Inputs DB"),
        (c2, tickers_kpi,      "Tickers CVM"),
        (c3, str(preserve_cnt),"PRESERVE"),
        (c4, str(ready_cnt),   "READY"),
        (c5, "1",              "PARTIAL"),
        (c6, str(len(dry_run)),"Dry-run OK"),
    ]:
        col.markdown(
            f'<div class="cov-kpi"><div class="cov-kpi-v">{val}</div>'
            f'<div class="cov-kpi-l">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Universo M017", "Dry-Run Matrix", "CVM Coverage", "Fair Values Preservados"
    ])

    # ── Tab 1: Universe ───────────────────────────────────────────────────
    with tab1:
        st.caption(f"32 tickers com model_status definido — M017 · {len(_UNIVERSE)} total")

        status_groups = {}
        for row in _UNIVERSE:
            status_groups.setdefault(row[1], []).append(row)

        for status_key in [
            "PRESERVE_EXISTING", "READY_TO_CALCULATE", "PARTIAL_INPUTS",
            "TECH_FALLBACK", "NEEDS_DATA", "NEEDS_RI_DOCS", "LEGACY_TICKER",
        ]:
            rows = status_groups.get(status_key, [])
            if not rows:
                continue
            emoji = _STATUS_EMOJI.get(status_key, "")
            color = _STATUS_COLOR.get(status_key, "#94A3B8")
            st.markdown(
                f'<div style="font-size:.7rem;font-weight:700;color:{color};'
                f'text-transform:uppercase;letter-spacing:.8px;margin:14px 0 6px 0;">'
                f'{emoji} {status_key} ({len(rows)})</div>',
                unsafe_allow_html=True,
            )
            for ticker, model_status, model, method, block, flags in rows:
                fv_str = f"R$ {_PRESERVE_FV[ticker]:.2f}" if ticker in _PRESERVE_FV else "—"
                n_metrics = kpis.get("coverage", {}).get(ticker, 0) if kpis else "—"
                dr = dry_map.get(ticker)
                dr_fv = f"R$ {dr['fair_value']}" if dr else "—"
                dr_up = f"{float(dr['upside_pct']):+.1f}%" if dr and dr.get("upside_pct") else "—"

                flag_html = ""
                if flags:
                    fc = "#F87171" if flags == "DISTRESSED" else "#FBBF24"
                    flag_html = (
                        f'<span style="background:#1E293B;border:1px solid {fc};'
                        f'border-radius:4px;padding:1px 6px;font-size:.56rem;color:{fc};">{flags}</span>'
                    )

                st.markdown(f"""
                <div style="background:#0F172A;border:1px solid #1E293B;border-radius:10px;
                     padding:10px 14px;margin-bottom:5px;
                     display:grid;grid-template-columns:80px 180px 90px 100px 80px 80px 1fr;
                     align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;">
                    <div style="font-size:.9rem;font-weight:700;color:#F1F5F9;">{ticker}</div>
                    <div style="font-size:.62rem;color:{color};font-weight:700;">{model_status}</div>
                    <div style="font-size:.62rem;color:#94A3B8;">{model}</div>
                    <div style="font-size:.62rem;color:#94A3B8;">{method}</div>
                    <div style="font-size:.62rem;color:#22D3EE;">{fv_str}</div>
                    <div style="font-size:.62rem;color:#4ADE80;">{dr_fv}</div>
                    <div style="font-size:.6rem;color:#64748B;text-align:right;">
                        {flag_html}
                        {f'<span style="color:#475569">{block}</span>' if block and not flags else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:.58rem;color:#334155;font-family:mono;margin-top:10px;">'
            'Legenda: FV Preservado = M015/M016 auditado · FV Dry-Run = M017-S05 write=False</div>',
            unsafe_allow_html=True,
        )

    # ── Tab 2: Dry-Run Matrix ─────────────────────────────────────────────
    with tab2:
        if not dry_run:
            st.warning("Dry-run matrix não encontrada: 12_PYTHON/docs/M017_S05_DRY_RUN_MATRIX.csv")
            return

        st.caption(
            f"{len(dry_run)} tickers · M017-S05 · write=False · "
            "asset_intelligence_snapshots não alterada"
        )

        st.markdown("""
        <div style="background:#0F172A;border:1px solid #1E293B;border-radius:8px;
             padding:6px 12px;margin-bottom:10px;
             display:grid;grid-template-columns:70px 70px 110px 90px 80px 140px;
             gap:8px;font-size:.58rem;color:#475569;font-family:mono;font-weight:700;text-transform:uppercase;">
            <div>Ticker</div><div>Upside</div><div>Fair Value</div>
            <div>Método</div><div>Conf.</div><div>Flags</div>
        </div>
        """, unsafe_allow_html=True)

        for row in dry_run:
            ticker = row.get("ticker", "—")
            fv     = row.get("fair_value", "—")
            method = row.get("method_used", "—")
            upside = row.get("upside_pct", "")
            conf   = row.get("confidence", "")
            flags  = row.get("quality_flags", "")
            status = row.get("status", "")

            try:
                upside_f    = float(upside)
                upside_str  = f"{upside_f:+.1f}%"
                upside_color = "#4ADE80" if upside_f > 0 else "#F87171"
            except (ValueError, TypeError):
                upside_str   = "—"
                upside_color = "#64748B"

            flag_html = ""
            if flags:
                fc = "#F87171" if flags == "DISTRESSED" else "#FBBF24"
                flag_html = (
                    f'<span style="background:#1E293B;border:1px solid {fc};'
                    f'border-radius:4px;padding:1px 6px;font-size:.58rem;color:{fc};">{flags}</span>'
                )

            st.markdown(f"""
            <div style="background:#0F172A;border:1px solid #1E293B;border-radius:8px;
                 padding:9px 12px;margin-bottom:5px;
                 display:grid;grid-template-columns:70px 70px 110px 90px 80px 1fr;
                 align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;">
                <div style="font-size:.85rem;font-weight:700;color:#F1F5F9;">{ticker}</div>
                <div style="font-size:.82rem;font-weight:700;color:{upside_color};">{upside_str}</div>
                <div style="font-size:.75rem;color:#22D3EE;">R$ {fv}</div>
                <div style="font-size:.62rem;color:#94A3B8;">{method}</div>
                <div style="font-size:.62rem;color:#64748B;">{conf}</div>
                <div>{flag_html}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:.58rem;color:#334155;margin-top:8px;">'
            '⚠️ Todos os fair_values acima são dry-run (write=False). '
            'M018 persiste com write=True após validação cruzada (range 0.1×–5.0× preço).</div>',
            unsafe_allow_html=True,
        )

    # ── Tab 3: CVM Coverage ───────────────────────────────────────────────
    with tab3:
        if not kpis:
            st.warning(
                "ingestion.db não encontrada. "
                "Defina FINANCIAL_INPUTS_DB_PATH ou verifique 12_PYTHON/data/ingestion.db"
            )
            return

        sources = kpis.get("sources", {})
        coverage = kpis.get("coverage", {})

        st.metric("Total de Registros",    f"{kpis.get('total',0):,}")
        st.metric("Tickers com CVM/DFP",   str(kpis.get("tickers","—")))
        st.metric("Métricas Distintas",    str(kpis.get("metrics","—")))

        st.markdown("**Fontes:**")
        for src, cnt in sources.items():
            st.markdown(f"- `{src}`: **{cnt:,}** registros")

        st.divider()
        st.markdown("**Cobertura por Ticker (métricas extraídas):**")

        rows_cov = []
        for ticker, _, model, _, _, _ in _UNIVERSE:
            n = coverage.get(ticker, 0)
            pct = f"{n/22*100:.0f}%" if n else "0%"
            rows_cov.append({
                "Ticker": ticker,
                "Modelo": model,
                "Métricas": n,
                "Cobertura (22)": pct,
                "Status CVM": "✅" if n >= 20 else ("⚠️" if n > 0 else "❌"),
            })

        import pandas as pd
        st.dataframe(
            pd.DataFrame(rows_cov),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("""
        <div style="font-size:.62rem;color:#475569;margin-top:8px;">
        Métricas extraídas: revenue, ebit, ebitda, net_income, ocf, capex, fcf,
        total_assets, cash, stdebt, ltdebt, gross_debt, net_debt, equity_book_value,
        shares_outstanding + 6 derivadas. Fonte: M017-S03 CVM_CSV + M017-S04 B3_MARKET_DATA.
        </div>
        """, unsafe_allow_html=True)

    # ── Tab 4: Fair Values Preservados ────────────────────────────────────
    with tab4:
        st.caption(
            "9 fair values auditados M015/M016 — não recalcular sem force_recalc=True explícito"
        )

        rows_fv = []
        for ticker, fv in _PRESERVE_FV.items():
            # get model from universe
            model_row = next((r for r in _UNIVERSE if r[0] == ticker), None)
            model  = model_row[2] if model_row else "—"
            method = model_row[3] if model_row else "—"
            rows_fv.append({
                "Ticker": ticker,
                "Modelo": model,
                "Método": method,
                "Fair Value": f"R$ {fv:.2f}",
                "Status": "🔒 PRESERVE_EXISTING",
                "M018 Action": "Não recalcular sem force_recalc=True",
            })

        import pandas as pd
        st.dataframe(
            pd.DataFrame(rows_fv),
            use_container_width=True,
            hide_index=True,
        )

        st.info(
            "**PETZ3** → LEGACY_TICKER permanente — bloqueado; não aparece na lista acima.  \n"
            "**AUAU3** → CNPJ nulo / sem CVM data — NEEDS_RI_DOCS.  \n"
            "**VALE3** → ri_docs=0 — aguarda CVM ingestion (SXX).  \n"
            "**PCAR3** → PARTIAL_INPUTS / DISTRESSED — EV/EBITDA only em M018."
        )

        st.caption(
            "M017 FECHADO 2026-05-26 · git commit 3ce801f · "
            "Próximo: M018 — Controlled Fair Value Calculation and Validation"
        )


main()
