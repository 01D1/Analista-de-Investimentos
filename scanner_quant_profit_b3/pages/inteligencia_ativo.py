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
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)
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
    status_chip,
    alert_block,
)
from src.data_quality.ri_sites import get_valid_ri_url_for_ticker
from src.dashboard.data import get_watchlist_summary, get_asset_detail


# ── Score helpers ────────────────────────────────────────────────────────────────

_CONFIDENCE_MAP = {
    "ALTA":   80.0,
    "ALTA_CONVERGENCIA": 85.0,
    "MEDIA":  50.0,
    "BAIXA":  25.0,
    "BLOQUEADO": 10.0,
    "DIVERGENCIA": 15.0,
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
            "Sem dados para {ticker}. "
            "Execute o pipeline para gerar a tese de investimento.".format(ticker=ticker),
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

    # Use REAL integrated_score from engine — not derived client-side
    overall_score = float(detail.get("integrated_score") or 0)
    confidence = detail.get("integrated_confidence") or confidence or ""
    ri_url = detail.get("ri_url") or None

    # Build dimensions from real engine data
    upside_f = float(upside_pct or 0)
    upside_score = min(100.0, max(0.0, 50.0 + upside_f * 1.5))
    conf_score = _CONFIDENCE_MAP.get(str(confidence or "").upper(), 40.0)
    tech_score = float(detail.get("technical_score_final") or 0)
    quant_sc = float(detail.get("quant_score") or 0)
    drivers = thesis.get("drivers", [])
    driver_count = min(100.0, len(drivers) * 25.0)
    risks = thesis.get("risks", [])
    high_risks = sum(1 for r in risks if str(r.get("severity", "")).upper() == "HIGH")
    risk_score = max(0.0, 100.0 - high_risks * 30.0)
    dimensions = {
        "Valuation": round(upside_score, 1),
        "Confianca": round(conf_score, 1),
        "Tecnico": round(tech_score, 1),
        "Quant": round(quant_sc, 1),
        "Baixo Risco": round(risk_score, 1),
    }

    # ── Hero section ──────────────────────────────────────────────────────────
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
        score_gauge(overall_score, label="Score de Investimento")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_radar:
        section_title("Radar de Qualidade", icon="")
        st.markdown('<div class="radar-wrap">', unsafe_allow_html=True)
        fig_radar = radar_chart(dimensions, ticker=ticker)
        if fig_radar is not None:
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

        # RI link and PDF inside tese tab (S06 — qualitative/RI status)
        col_ri, col_pdf = st.columns([1, 1])
        with col_ri:
            if ri_url:
                st.markdown(
                    f'<div style="margin-bottom:6px;">{status_chip("APPROVED_FOR_STUDY", label="RI disponível")}</div>',
                    unsafe_allow_html=True,
                )
                st.link_button("Acessar Site de RI", ri_url, use_container_width=True)
            else:
                st.markdown(
                    f'<div style="margin-bottom:6px;">{status_chip("EMPTY", label="RI pendente de validação")}</div>',
                    unsafe_allow_html=True,
                )

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
            driver_list("Drivers", thesis.get("drivers", []))
        with col_r:
            section_title("Riscos", icon="")
            risk_list(thesis.get("risks", []))

    with tab_debug:
        debug_expander(detail)

    # ── Valuation Tab (S04) ───────────────────────────────────────────────────
    val_available = detail.get("valuation_available", False)
    val_source = detail.get("valuation_source", "none")
    val_method = detail.get("valuation_method", "")
    val_date = detail.get("valuation_date", "")
    val_fair_value = detail.get("fair_value", 0.0)
    val_current_price = detail.get("current_price")
    val_market_price = detail.get("market_price")
    val_upside_pct = detail.get("upside_pct")
    val_upside_label = detail.get("upside_label", "N/A")
    val_confidence = detail.get("valuation_confidence", 0.0)
    val_source_file = detail.get("source_file", "")
    val_divergence = detail.get("divergence_vs_scanner_quant")

    tab_val = st.tabs(["   Valuation"])[0]
    with tab_val:
        # Source status chip (S05)
        if val_available:
            src_status = "APPROVED_FOR_STUDY"
            src_label = val_source.upper().replace("_", " ")
        elif val_source == "scanner_quant_db":
            src_status = "MONITOR_ONLY"
            src_label = "SCANNER QUANT DB"
        else:
            src_status = "EMPTY"
            src_label = "SEM VALUATION"

        st.markdown(
            f'<div style="margin-bottom:16px;">'
            f'{status_chip(src_status, label=src_label)}'
            f'<div style="font-family:var(--font-mono);font-size:.62rem;color:var(--fg-5);'
            f'margin-top:6px;">{src_status}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Valuation metrics strip
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            fv_display = f"R$ {val_fair_value:.2f}" if val_fair_value and val_fair_value > 0 else "—"
            st.metric("Preço Justo", fv_display, delta=None)
        with col2:
            cp_display = f"R$ {val_current_price:.2f}" if val_current_price else "—"
            st.metric("Cotação Atual", cp_display, delta=None)
        with col3:
            mp_display = f"R$ {val_market_price:.2f}" if val_market_price else "—"
            st.metric("Preço de Mercado", mp_display, delta=None)
        with col4:
            up_display = val_upside_label if val_upside_label != "N/A" else "—"
            up_color = "normal" if val_upside_pct and val_upside_pct >= 0 else "inverse"
            st.metric("Upside", up_display, delta=None, delta_color=up_color)
        with col5:
            conf_display = f"{val_confidence:.0%}" if val_confidence else "—"
            st.metric("Confiança", conf_display, delta=None)

        # Divergence alert (S05)
        if val_divergence:
            sq_fv = val_divergence.get("scanner_quant_fair_value", 0)
            pipe_fv = val_divergence.get("pipeline_fair_value", 0)
            div_pct = val_divergence.get("divergence_pct", 0)
            note = val_divergence.get("note", "")
            alert_kind = "warn" if abs(div_pct) < 10 else "error"
            div_pct_str = f"{div_pct:+.1f}%"
            body = (
                f"scanner_quant.db: R$ {sq_fv:.2f} · Pipeline DCF: R$ {pipe_fv:.2f} · Δ {div_pct_str}\n"
                f"{note}"
            )
            st.markdown(
                alert_block(alert_kind, "Divergência: scanner_quant vs pipeline", body),
                unsafe_allow_html=True,
            )

        # Full fields table in .panel (S05)
        st.markdown('<div class="panel" style="margin-top:12px; padding:16px 20px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:var(--font-mono);font-size:.62rem;font-weight:800;color:var(--fg-5);text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px;">Campos de Valuation</div>', unsafe_allow_html=True)

        def _val_row(label: str, value: str, highlight: bool = False) -> str:
            hl = "background:rgba(34,197,94,0.04);" if highlight else ""
            return (
                f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                f'border-bottom:1px solid var(--border-1);{hl}">'
                f'<span style="font-family:var(--font-mono);font-size:.68rem;color:var(--fg-5);">{label}</span>'
                f'<span style="font-family:var(--font-mono);font-size:.68rem;color:var(--fg-1);font-weight:600;">{value}</span>'
                f'</div>'
            )

        rows_htm = ""
        rows_htm += _val_row("valuation_available", str(val_available))
        rows_htm += _val_row("valuation_source", val_source)
        rows_htm += _val_row("valuation_method", val_method or "—")
        rows_htm += _val_row("valuation_date", val_date or "—")
        rows_htm += _val_row("current_price", f"R$ {val_current_price:.2f}" if val_current_price else "—", highlight=True)
        rows_htm += _val_row("market_price", f"R$ {val_market_price:.2f}" if val_market_price else "—")
        rows_htm += _val_row("fair_value", f"R$ {val_fair_value:.2f}" if val_fair_value and val_fair_value > 0 else "—", highlight=True)
        rows_htm += _val_row("upside_pct", f"{val_upside_pct:.2f}%" if val_upside_pct is not None else "—", highlight=True)
        rows_htm += _val_row("upside_label", val_upside_label)
        rows_htm += _val_row("valuation_confidence", f"{val_confidence:.0%}" if val_confidence else "—")
        rows_htm += _val_row("source_file", val_source_file or "—")

        st.markdown(rows_htm, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Empty state for unavailable valuation
        if not val_available and val_source == "none":
            st.caption("Valuation não disponível para este ticker. Execute o pipeline de valuation para gerar.")


main()
