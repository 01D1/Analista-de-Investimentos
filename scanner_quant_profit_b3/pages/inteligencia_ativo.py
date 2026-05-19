"""Análise de Ativo — Premium UI (Phase 5 DEL-01/DEL-05)."""
from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup (mirrors original) ─────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
if _PIPELINE_ROOT in sys.path:
    sys.path.remove(_PIPELINE_ROOT)
sys.path.insert(0, _PIPELINE_ROOT)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    hero_section,
    kpi_strip,
    score_gauge,
    score_breakdown_bars,
    thesis_card,
    driver_list,
    risk_list,
    radar_chart,
    section_title,
    empty_state,
    debug_expander,
    positioning_badge,
    metric_table_row,
)
from src.data_quality.ri_sites import get_valid_ri_url_for_ticker
from src.dashboard.data import get_watchlist_summary, get_asset_detail


# ── Derived score helpers ──────────────────────────────────────────────────────

_POSITIVE_WORDS = {
    "crescimento", "forte", "lider", "margem", "expansao", "lucro",
    "alta", "potencial", "oportunidade", "solido", "positivo", "ganho",
    "robusto", "dinamico", "avanco", "superou",
}

_CONFIDENCE_MAP = {
    "ALTA":   80.0,
    "ALTA_CONVERGENCIA": 85.0,
    "MEDIA":  50.0,
    "BAIXA":  25.0,
    "BLOQUEADO": 10.0,
    "DIVERGENCIA": 15.0,
}


def _bull_sentiment(text: str) -> float:
    """Count positive-word density → 0-100."""
    if not text:
        return 40.0
    words = text.lower().split()
    if not words:
        return 40.0
    hits = sum(1 for w in words if any(p in w for p in _POSITIVE_WORDS))
    return min(100.0, (hits / len(words)) * 800)


def _derive_score(upside_pct, confidence_raw: str, bull_case: str) -> float:
    """Map raw data to an overall 0-100 score."""
    try:
        upside_f = float(upside_pct or 0)
    except (TypeError, ValueError):
        upside_f = 0.0

    upside_score = min(100.0, max(0.0, 50.0 + upside_f * 1.5))
    conf_score   = _CONFIDENCE_MAP.get(str(confidence_raw or "").upper(), 40.0)
    bull_score   = _bull_sentiment(bull_case)
    return round((upside_score * 0.45 + conf_score * 0.35 + bull_score * 0.20), 1)


def _build_dimensions(thesis: dict, upside_pct, confidence_raw: str) -> dict[str, float]:
    """Build a 5-dimension dict for radar + breakdown bars."""
    try:
        upside_f = float(upside_pct or 0)
    except (TypeError, ValueError):
        upside_f = 0.0

    upside_score  = min(100.0, max(0.0, 50.0 + upside_f * 1.5))
    conf_score    = _CONFIDENCE_MAP.get(str(confidence_raw or "").upper(), 40.0)
    bull_score    = _bull_sentiment(thesis.get("bull_case", ""))
    drivers       = thesis.get("drivers", [])
    driver_count  = min(100.0, len(drivers) * 25.0)

    # risk level = inverted HIGH count
    risks = thesis.get("risks", [])
    high_risks = sum(1 for r in risks if str(r.get("severity", "")).upper() == "HIGH")
    risk_score = max(0.0, 100.0 - high_risks * 30.0)

    return {
        "Valuation":   round(upside_score, 1),
        "Confianca":   round(conf_score, 1),
        "Bull Thesis": round(bull_score, 1),
        "Drivers":     round(driver_count, 1),
        "Baixo Risco": round(risk_score, 1),
    }


# ── Page ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(
        """
<div class="page-header">
  <div class="page-header-title">Analise de Ativo</div>
  <div class="page-header-sub">Tese de investimento gerada pelo pipeline de inteligencia quantitativa</div>
</div>""",
        unsafe_allow_html=True,
    )

    # ── Ticker selector ──────────────────────────────────────────────────────
    rows = get_watchlist_summary()
    if not rows:
        empty_state(
            "Nenhuma tese gerada ainda.\n"
            "Execute: python -m src.main daemon para iniciar o pipeline.",
            icon="",
        )
        st.stop()

    tickers = sorted(set(r["ticker"] for r in rows))
    ticker = st.selectbox("Selecionar ativo:", tickers)

    detail = get_asset_detail(ticker)
    if detail is None:
        empty_state(
            "Sem dados para {0}. "
            "Execute o pipeline para gerar a tese de investimento.".format(ticker),
            icon="",
        )
        st.stop()

    thesis       = detail["thesis"]
    upside_pct   = detail.get("dcf", {}).get("upside_pct")
    generated_at = detail.get("generated_at", "—")
    positioning  = thesis.get("positioning", "MANTER")
    fair_value   = thesis.get("fair_value_brl", 0.0)
    confidence   = thesis.get("confidence", "") or detail.get("confidence", "")

    # row-level confidence fallback
    if not confidence:
        matching = [r for r in rows if r.get("ticker") == ticker]
        if matching:
            confidence = matching[0].get("confidence", "")

    overall_score = _derive_score(upside_pct, confidence, thesis.get("bull_case", ""))
    dimensions    = _build_dimensions(thesis, upside_pct, confidence)

    ri_url = get_valid_ri_url_for_ticker(ticker)

    # ── Hero section ─────────────────────────────────────────────────────────
    hero_section(
        ticker=ticker,
        nome=ticker,
        setor="",
        positioning=positioning,
        score=overall_score,
        upside=float(upside_pct) if upside_pct is not None else None,
    )

    # ── KPI Strip ────────────────────────────────────────────────────────────
    upside_str = "{0:+.1f}%".format(float(upside_pct)) if upside_pct is not None else "—"
    upside_color = "green" if (upside_pct or 0) >= 0 else "red"

    conf_upper = str(confidence or "").upper()
    conf_color_map = {"ALTA": "green", "ALTA_CONVERGENCIA": "green",
                      "MEDIA": "amber", "BAIXA": "red", "BLOQUEADO": "red"}
    conf_color = conf_color_map.get(conf_upper, "gray")

    gen_display = str(generated_at)[:16] if generated_at else "—"

    kpi_strip([
        {"label": "Preco Justo",    "value": "R$ {0:.2f}".format(float(fair_value or 0)),
         "color": "blue"},
        {"label": "Upside DCF",     "value": upside_str,
         "color": upside_color},
        {"label": "Posicionamento", "value": positioning,
         "color": conf_color_map.get(positioning, "gray")},
        {"label": "Confianca",      "value": confidence or "—",
         "color": conf_color},
        {"label": "Score Geral",    "value": "{0:.0f} / 100".format(overall_score),
         "color": "blue"},
        {"label": "Atualizado em",  "value": gen_display,
         "color": "gray"},
    ])

    # ── Score Gauge + Radar side-by-side ─────────────────────────────────────
    col_gauge, col_radar = st.columns([1, 1])

    with col_gauge:
        section_title("Score Geral", icon="")
        st.markdown('<div class="score-gauge-wrap">', unsafe_allow_html=True)
        fig_gauge = score_gauge(overall_score, label="Score de Investimento")
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_radar:
        section_title("Radar de Qualidade", icon="")
        st.markdown('<div class="radar-wrap">', unsafe_allow_html=True)
        fig_radar = radar_chart(dimensions, ticker=ticker)
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Score Breakdown ───────────────────────────────────────────────────────
    section_title("Decomposicao do Score", icon="")
    score_breakdown_bars(dimensions)

    # ── 3 Tabs: Tese | Drivers & Riscos | Debug ───────────────────────────────
    tab_tese, tab_drivers, tab_debug = st.tabs(
        ["   Tese de Investimento", "   Drivers & Riscos", "   Debug"]
    )

    with tab_tese:
        section_title("Bull Case & Bear Case", icon="")
        thesis_card(
            bull_case=thesis.get("bull_case", "—"),
            bear_case=thesis.get("bear_case", "—"),
            drivers=thesis.get("drivers", []),
            risks=thesis.get("risks", []),
        )

        # RI link and PDF inside tese tab
        col_ri, col_pdf = st.columns([1, 1])
        with col_ri:
            if ri_url:
                st.link_button("Acessar Site de RI", ri_url, use_container_width=True)
            else:
                st.caption("RI pendente de validacao")

        with col_pdf:
            try:
                from src.delivery.pdf_report import ReportGenerator
                pdf_bytes = ReportGenerator().generate(ticker, detail)
                st.download_button(
                    label="Baixar Relatorio PDF",
                    data=pdf_bytes,
                    file_name="relatorio_{0}.pdf".format(ticker),
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception:
                st.error("PDF indisponivel — verifique o pipeline.")

    with tab_drivers:
        col_d, col_r = st.columns([1, 1])
        with col_d:
            section_title("Drivers de Investimento", icon="")
            driver_list(thesis.get("drivers", []))
        with col_r:
            section_title("Riscos", icon="")
            risk_list(thesis.get("risks", []))

    with tab_debug:
        debug_expander(detail)


main()
