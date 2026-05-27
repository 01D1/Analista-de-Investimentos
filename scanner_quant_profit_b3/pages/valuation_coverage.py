"""Cobertura de Valuation — Universo de 32 empresas

Abas:
  1. Universo de Cobertura    — 32 tickers com filtros e chips de status
  2. Simulação dos Modelos    — dry-run validado (write=False)
  3. Cobertura CVM/DFP        — valuation_financial_inputs por ticker
  4. Preços Justos            — 9 fair values auditados (wl-card + upside)

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

_CACHE_TTL = 300  # 5 minutes

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
    ("ABCB4",  "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("BBAS3",  "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("BBDC4",  "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("BPAC11", "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("BRSR6",  "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("ITUB4",  "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("SANB11", "PRESERVE_EXISTING",   "Banco",          "P/BV",      "",                                ""),
    ("PETR4",  "PRESERVE_EXISTING",   "Commodity",      "DCF/FCFF",  "",                                ""),
    ("WEGE3",  "PRESERVE_EXISTING",   "Industrial",     "DCF/FCFF",  "",                                ""),
    ("EGIE3",  "READY_TO_CALCULATE",  "Utilidade",      "DCF/FCFF",  "",                                ""),
    ("SBSP3",  "READY_TO_CALCULATE",  "Utilidade",      "EV/EBITDA", "",                                "FCF negativo esperado"),
    ("TAEE11", "READY_TO_CALCULATE",  "Utilidade",      "DCF/FCFF",  "",                                ""),
    ("AZZA3",  "READY_TO_CALCULATE",  "Varejo",         "DCF/FCFF",  "",                                ""),
    ("LREN3",  "READY_TO_CALCULATE",  "Varejo",         "DCF/FCFF",  "",                                ""),
    ("MGLU3",  "READY_TO_CALCULATE",  "Varejo",         "EV/EBITDA", "",                                "FCF em revisão"),
    ("VIVA3",  "READY_TO_CALCULATE",  "Varejo",         "DCF/FCFF",  "",                                ""),
    ("PRIO3",  "READY_TO_CALCULATE",  "Commodity",      "DCF/FCFF",  "",                                ""),
    ("RECV3",  "READY_TO_CALCULATE",  "Commodity",      "EV/EBITDA", "",                                "FCF negativo esperado"),
    ("FLRY3",  "READY_TO_CALCULATE",  "Industrial",     "DCF/FCFF",  "",                                ""),
    ("HYPE3",  "READY_TO_CALCULATE",  "Industrial",     "DCF/FCFF",  "",                                ""),
    ("KLBN11", "READY_TO_CALCULATE",  "Industrial",     "DCF/FCFF",  "",                                ""),
    ("RADL3",  "READY_TO_CALCULATE",  "Industrial",     "DCF/FCFF",  "",                                ""),
    ("RAIL3",  "READY_TO_CALCULATE",  "Industrial",     "EV/EBITDA", "",                                ""),
    ("RENT3",  "READY_TO_CALCULATE",  "Industrial",     "EV/EBITDA", "",                                ""),
    ("SUZB3",  "READY_TO_CALCULATE",  "Industrial",     "DCF/FCFF",  "",                                ""),
    ("VAMO3",  "READY_TO_CALCULATE",  "Industrial",     "EV/EBITDA", "",                                "FCF negativo esperado"),
    ("PCAR3",  "PARTIAL_INPUTS",      "Varejo",         "EV/EBITDA", "Empresa em recuperação judicial", "Distressed"),
    ("VIVT3",  "TECH_FALLBACK",       "Industrial",     "EV/EBITDA", "Inputs CVM pendentes",            ""),
    ("VALE3",  "NEEDS_DATA",          "Commodity",      "DCF/FCFF",  "ri_docs=0",                       ""),
    ("AUAU3",  "NEEDS_RI_DOCS",       "—",              "—",         "CNPJ nulo — sem dados CVM",       ""),
    ("NTCO3",  "NEEDS_RI_DOCS",       "Varejo",         "DCF/FCFF",  "Docs RI insuficientes",           ""),
    ("PETZ3",  "LEGACY_TICKER",       "Varejo",         "—",         "Encerrada — fusão consumada",     ""),
]

_PRESERVE_FV: dict[str, float] = {
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

_STATUS_CHIP: dict[str, str] = {
    "PRESERVE_EXISTING":  "manual",
    "READY_TO_CALCULATE": "approved",
    "PARTIAL_INPUTS":     "degraded",
    "TECH_FALLBACK":      "monitor",
    "NEEDS_DATA":         "blocked",
    "NEEDS_RI_DOCS":      "blocked",
    "LEGACY_TICKER":      "paper",
}

_STATUS_ORDER = [
    "PRESERVE_EXISTING", "READY_TO_CALCULATE", "PARTIAL_INPUTS",
    "TECH_FALLBACK", "NEEDS_DATA", "NEEDS_RI_DOCS", "LEGACY_TICKER",
]

# Fallback prices (2026-05-22)
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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def _badge_html(text: str, variant: str = "cyan") -> str:
    return f'<span class="badge badge-{variant}">{text}</span>'


def _chip_html(text: str, variant: str = "manual") -> str:
    return f'<span class="chip chip-{variant}"><span class="dot"></span>{text}</span>'


def _method_badge(method: str) -> str:
    if not method or method == "—":
        return '<span style="color:var(--fg-6);">—</span>'
    variant = "cyan" if ("DCF" in method or "P/BV" in method) else "violet"
    return _badge_html(method, variant)


def _status_chip(status_key: str) -> str:
    label = _STATUS_PT.get(status_key, status_key)
    variant = _STATUS_CHIP.get(status_key, "paper")
    return _chip_html(label, variant)


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_market_prices() -> dict[str, dict]:
    """Load latest market prices from asset_intelligence_snapshots, with fallback."""
    result: dict[str, dict] = dict(_PRICES_FALLBACK)
    if not _SCANNER_DB.exists():
        return result
    try:
        conn = sqlite3.connect(str(_SCANNER_DB))
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


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
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


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_preliminary_sanity_map() -> dict[str, int | None]:
    """Load {ticker: sanity_check_passed} for M018_CONTROLLED tickers (read-only).

    Returns empty dict if ingestion.db is unavailable.
    Never writes to DB.
    """
    if _INGESTION_DB is None:
        return {}
    try:
        conn = sqlite3.connect(str(_INGESTION_DB))
        rows = conn.execute("""
            SELECT ticker, sanity_check_passed
            FROM valuation_results
            WHERE source = 'M018_CONTROLLED'
              AND status  = 'preliminary'
        """).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def _load_preliminary_fv_map() -> dict[str, dict]:
    """Load {ticker: {preliminary_fair_value, market_price, upside_pct, ...}} (read-only).

    Returns empty dict if ingestion.db is unavailable.
    Never writes to DB.
    """
    if _INGESTION_DB is None:
        return {}
    try:
        conn = sqlite3.connect(str(_INGESTION_DB))
        rows = conn.execute("""
            SELECT ticker, preliminary_fair_value, market_price, upside_pct,
                   method_used, confidence, sanity_check_passed
            FROM valuation_results
            WHERE source = 'M018_CONTROLLED'
              AND status  = 'preliminary'
        """).fetchall()
        conn.close()
        return {
            r[0]: {
                "preliminary_fair_value": r[1],
                "market_price":           r[2],
                "upside_pct":             r[3],
                "method_used":            r[4],
                "confidence":             r[5],
                "sanity_check_passed":    r[6],
            }
            for r in rows
        }
    except Exception:
        return {}


# ── Page render ────────────────────────────────────────────────────────────────

def main() -> None:
    kpis        = _load_ingestion_kpis()
    dry_run     = _load_dry_run_matrix()
    dry_map     = {r["ticker"]: r for r in dry_run}
    market      = _load_market_prices()
    sanity_map  = _load_preliminary_sanity_map()   # {ticker: sanity_check_passed}
    prelim_map  = _load_preliminary_fv_map()        # {ticker: {fv, price, upside, ...}}

    ready_cnt    = sum(1 for r in _UNIVERSE if r[1] == "READY_TO_CALCULATE")
    preserve_cnt = sum(1 for r in _UNIVERSE if r[1] == "PRESERVE_EXISTING")
    passed_cnt   = sum(1 for v in sanity_map.values() if v == 1)
    pending_cnt  = sum(1 for v in sanity_map.values() if v != 1)

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
      <div class="page-header-title">Cobertura de Valuation</div>
      <div class="page-header-sub">
        32 empresas · 47.621 registros financeiros · 18 valores preliminares
        · 9 preços justos preservados · Referência: 2025-12-31
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI strip ─────────────────────────────────────────────────────────────
    total_kpi = f"{kpis.get('total', 0):,}".replace(",", ".") if kpis else "—"
    kpi_strip([
        {"label": "Base financeira",         "value": total_kpi,                                      "color": "cyan"},
        {"label": "Empresas CVM",            "value": str(kpis.get("tickers", "—")) if kpis else "—", "color": "cyan"},
        {"label": "Preço justo preservado",  "value": str(preserve_cnt),                              "color": "green"},
        {"label": "Valor preliminar",        "value": str(len(prelim_map)) or str(ready_cnt),         "color": "violet"},
        {"label": "Passou na checagem",      "value": str(passed_cnt) if sanity_map else "—",         "color": "green"},
        {"label": "Requer validação",        "value": str(pending_cnt) if sanity_map else "—",        "color": "amber"},
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
        # Disclaimer M018-S04
        st.markdown(
            '<div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.3);'
            'border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:.68rem;'
            'color:var(--warn-500);line-height:1.5;">'
            '<strong>⚠️ Valores Preliminares:</strong> '
            'Os valores preliminares são resultados do motor quantitativo e ainda não '
            'representam recomendação final.</div>',
            unsafe_allow_html=True,
        )

        # Filters
        f_col1, f_col2, f_col3, _ = st.columns([1, 1, 1, 0.5])
        with f_col1:
            _FILTER_CATS = [
                "Todos",
                "Preservado",
                "Preliminar — passou na checagem",
                "Preliminar — requer validação",
                "Dados parciais",
                "Ticker legado",
                "Aguardando dados",
            ]
            status_filter = st.selectbox("Categoria", options=_FILTER_CATS, key="cov_status")
        with f_col2:
            all_sectors = sorted({r[2] for r in _UNIVERSE if r[2] != "—"})
            sector_filter = st.selectbox(
                "Setor / Modelo",
                options=["Todos os setores"] + all_sectors,
                key="cov_sector",
            )
        with f_col3:
            all_methods = sorted({r[3] for r in _UNIVERSE if r[3] != "—"})
            method_filter = st.selectbox(
                "Método",
                options=["Todos os métodos"] + all_methods,
                key="cov_method",
            )

        # Apply filters
        filtered: list[tuple] = list(_UNIVERSE)
        _passed_set = {t for t, s in sanity_map.items() if s == 1}

        if status_filter != "Todos":
            if status_filter == "Preservado":
                filtered = [r for r in filtered if r[1] == "PRESERVE_EXISTING"]
            elif status_filter == "Preliminar — passou na checagem":
                filtered = [r for r in filtered
                            if r[1] == "READY_TO_CALCULATE" and r[0] in _passed_set]
            elif status_filter == "Preliminar — requer validação":
                filtered = [r for r in filtered
                            if r[1] == "READY_TO_CALCULATE" and r[0] not in _passed_set]
            elif status_filter == "Dados parciais":
                filtered = [r for r in filtered if r[1] == "PARTIAL_INPUTS"]
            elif status_filter == "Ticker legado":
                filtered = [r for r in filtered if r[1] == "LEGACY_TICKER"]
            elif status_filter == "Aguardando dados":
                filtered = [r for r in filtered
                            if r[1] in ("NEEDS_DATA", "NEEDS_RI_DOCS", "TECH_FALLBACK")]

        if sector_filter != "Todos os setores":
            filtered = [r for r in filtered if r[2] == sector_filter]
        if method_filter != "Todos os métodos":
            filtered = [r for r in filtered if r[3] == method_filter]

        st.caption(f"Exibindo {len(filtered)} de {len(_UNIVERSE)} empresas")

        if not filtered:
            st.markdown(
                '<div style="padding:24px;text-align:center;color:var(--fg-5);">'
                'Nenhuma empresa encontrada para os filtros selecionados.</div>',
                unsafe_allow_html=True,
            )
        else:
            table_rows = []
            for ticker, model_status, model, method, block, flags in filtered:
                fv_str = _fmt_brl(_PRESERVE_FV[ticker]) if ticker in _PRESERVE_FV else "—"

                prelim = prelim_map.get(ticker)
                if prelim and prelim.get("preliminary_fair_value") is not None:
                    pfv = prelim["preliminary_fair_value"]
                    pup = prelim.get("upside_pct")
                    pfv_str = _fmt_brl(pfv)
                    try:
                        pup_str = f"{float(pup):+.1f}%"
                    except (TypeError, ValueError):
                        pup_str = "—"
                else:
                    pfv_str = "—"
                    pup_str = "—"

                if model_status == "READY_TO_CALCULATE":
                    if ticker in _passed_set:
                        status_str = "✅ Passou na checagem"
                    elif ticker in sanity_map:
                        status_str = "⚠️ Requer validação"
                    else:
                        status_str = _status_chip(model_status)
                else:
                    status_str = _status_chip(model_status)

                table_rows.append({
                    "Ticker":               ticker,
                    "Modelo":              model,
                    "Método":              method,
                    "Preço Justo Pres.":   fv_str,
                    "Valor Prelim.":       pfv_str,
                    "Up/Downside Prelim.": pup_str,
                    "Status":              status_str,
                    "Alertas":             flags if flags else "—",
                })

            df_universe = pd.DataFrame(table_rows)
            st.dataframe(df_universe, use_container_width=True, hide_index=True, height=400)

        st.markdown(
            '<div style="font-size:.58rem;color:var(--fg-6);font-family:monospace;margin-top:10px;">'
            'Preço Justo Preservado = auditado M015/M016 · '
            'Valor Preliminar = M018-S04 (read-only) · Não aprovado</div>',
            unsafe_allow_html=True,
        )

    # ── Tab 2: Simulação dos Modelos ──────────────────────────────────────────
    with tab2:
        if not dry_run:
            st.markdown(alert_block(
                "warn",
                "Simulação não disponível",
                "Matriz de simulação não encontrada. "
                "Execute o dry-run para gerar os resultados de simulação.",
            ), unsafe_allow_html=True)
        else:
            st.markdown(alert_block(
                "info",
                "Simulação com write=False — nenhum valor foi persistido",
                f"{len(dry_run)} empresas simuladas. "
                "asset_intelligence_snapshots não foi alterada. "
                "Próxima etapa persiste com write=True após validação cruzada (range 0,1× – 5,0× preço).",
            ), unsafe_allow_html=True)

            table_rows = []
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
                    up_str = f"{float(upside):+.1f}%"
                except (TypeError, ValueError):
                    up_str = "—"

                try:
                    conf_str = f"{float(conf_raw):.0%}"
                except (TypeError, ValueError):
                    conf_str = "—"

                table_rows.append({
                    "Ticker":        ticker,
                    "Valor Just.":  fv_str,
                    "Up/Downside":  up_str,
                    "Método":       method,
                    "Confiança":    conf_str,
                    "Alertas":      flags if flags else "—",
                })

            df_sim = pd.DataFrame(table_rows)
            st.dataframe(df_sim, use_container_width=True, hide_index=True, height=400)

            st.markdown(
                '<div style="font-size:.58rem;color:var(--fg-6);margin-top:10px;">'
                'Todos os valores acima são simulação (write=False). '
                'Próxima etapa persiste com write=True após validação cruzada (0,1× – 5,0× preço).</div>',
                unsafe_allow_html=True,
            )

    # ── Tab 3: Cobertura CVM/DFP ──────────────────────────────────────────────
    with tab3:
        if not kpis:
            st.warning(
                "ingestion.db não encontrada. "
                "Defina FINANCIAL_INPUTS_DB_PATH ou verifique 12_PYTHON/data/ingestion.db"
            )
        else:
            sources  = kpis.get("sources", {})
            coverage = kpis.get("coverage", {})

            kpi_strip([
                {"label": "Total de registros",   "value": f"{kpis.get('total', 0):,}".replace(",", "."), "color": "cyan"},
                {"label": "Empresas com CVM/DFP", "value": str(kpis.get("tickers", "—")),                 "color": "cyan"},
                {"label": "Métricas distintas",   "value": str(kpis.get("metrics", "—")),                 "color": "violet"},
            ])

            section_title("Fontes de dados", icon="")
            for src, cnt in sources.items():
                st.markdown(
                    f'<div style="font-size:.75rem;color:var(--fg-3);padding:4px 0;">'
                    f'<span style="font-family:var(--font-mono);color:var(--brand-400);">{src}</span>'
                    f' &nbsp;→&nbsp; <strong>{cnt:,}</strong> registros</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            section_title("Cobertura por Empresa (métricas extraídas)", icon="")

            table_rows = []
            for ticker, _, model, _, _, _ in _UNIVERSE:
                cov = coverage.get(ticker, {"n_metrics": 0, "last_period": None})
                n   = cov["n_metrics"]
                period = cov.get("last_period") or "—"
                pct = f"{n / 22 * 100:.0f}%" if n else "0%"

                if n >= 22:
                    status_str = "✅ Completo"
                elif n > 0:
                    status_str = "⚠️ Parcial"
                else:
                    status_str = "❌ Sem dados"

                table_rows.append({
                    "Ticker":    ticker,
                    "Modelo":    model,
                    "Métricas":  n,
                    "Cobertura": pct,
                    "Período":   period,
                    "Status":    status_str,
                })

            df_cvm = pd.DataFrame(table_rows)
            st.dataframe(df_cvm, use_container_width=True, hide_index=True, height=400)

            st.markdown(
                '<div style="font-size:.62rem;color:var(--fg-6);margin-top:8px;">'
                '22 métricas: revenue · ebit · ebitda · net_income · operating_cash_flow · capex · '
                'free_cash_flow · total_assets · cash_and_equivalents · short_term_debt · long_term_debt · '
                'gross_debt · net_debt · equity_book_value · shares_outstanding + 7 derivadas. '
                'Fonte: CVM_CSV + B3_MARKET_DATA.</div>',
                unsafe_allow_html=True,
            )

    # ── Tab 4: Preços Justos ──────────────────────────────────────────────────
    with tab4:
        st.caption(
            "9 preços justos auditados — não recalcular sem force_recalc=True explícito"
        )

        # Disclaimer M018-S04
        st.markdown(
            '<div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.3);'
            'border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:.68rem;'
            'color:var(--warn-500);line-height:1.5;">'
            '<strong>⚠️ Valores Preliminares (M018-S04):</strong> '
            'Os valores preliminares são resultados do motor quantitativo e ainda não '
            'representam recomendação final. '
            'Para ver os 18 valores preliminares, acesse a aba '
            '<strong>Preços Justos Preliminares</strong> no Valuation Hub.</div>',
            unsafe_allow_html=True,
        )

        # wl-card grid: 3 columns
        cols = st.columns(3)
        for idx, (ticker, fv) in enumerate(_PRESERVE_FV.items()):
            col_idx = idx % 3
            model_row = next((r for r in _UNIVERSE if r[0] == ticker), None)
            model  = model_row[2] if model_row else "—"
            method = model_row[3] if model_row else "—"

            market_info = market.get(ticker, {})
            price = market_info.get("price")
            name  = market_info.get("name", "")
            date  = market_info.get("date", "")

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
                f'<div style="font-size:.6rem;color:var(--fg-5);font-family:var(--font-mono);">'
                f'{name}</div>'
                if name else ""
            )
            variant = "cyan" if ("DCF" in method or "P/BV" in method) else "violet"
            date_html = f" · {date}" if date else ""

            with cols[col_idx]:
                st.markdown(f"""
                <div class="wl-card {card_class}" style="margin-bottom:12px;">
                  <div class="top">
                    <div>
                      <div class="tk">{ticker}</div>
                      {name_html}
                      <div style="font-size:.58rem;color:var(--fg-6);font-family:var(--font-mono);">{model}</div>
                    </div>
                    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;">
                      <span class="badge badge-cyan">Preservado</span>
                      <span class="badge badge-{variant}">{method}</span>
                    </div>
                  </div>
                  <div class="grid">
                    <div class="item">Mercado<span class="v">{price_str}</span></div>
                    <div class="item">Preço justo<span class="v" style="color:var(--fg-1);">{fv_str}</span></div>
                    <div class="item">Upside / Downside
                      <span class="v" style="color:{upside_color};font-weight:900;">{upside_str}</span>
                    </div>
                    <div class="item">Fonte<span class="v">M015/M016</span></div>
                  </div>
                  <div class="meta">Auditado{date_html}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(alert_block(
            "warn",
            "Atenção — ativos com restrição de cálculo",
            "PETZ3 — Ticker legado permanente — bloqueado.  "
            "AUAU3 — CNPJ nulo / sem dados CVM — aguardando mapeamento.  "
            "VALE3 — ri_docs=0 — aguarda ingestion CVM.  "
            "PCAR3 — Dados parciais / Distressed — EV/EBITDA único aplicável.",
        ), unsafe_allow_html=True)

        st.caption(
            "Base fechada · Próximo: cálculo controlado com write=True após validação cruzada"
        )


main()
