"""Painel Macroeconômico — Phase 5 DEL-01."""
from __future__ import annotations

import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
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
import plotly.graph_objects as go

from src.ui.styles import PREMIUM_CSS  # canonical design tokens
from src.ui.components import status_chip, alert_block, empty_state, kpi_card, section_title
from src.dashboard.data import get_macro_panel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SERIES_TITLES = {
    "selic":       "Selic (% a.a.)",
    "ipca_12m":    "IPCA Acumulado 12m (%)",
    "ptax":        "PTAX (R$/USD)",
    "cds_brasil":  "CDS Brasil (bps)",
    "pib_nominal": "PIB Nominal (R$ bi)",
}

_SERIES_ORDER = ["selic", "ipca_12m", "ptax", "cds_brasil", "pib_nominal"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_chart(name: str, series_data: list[dict]) -> go.Figure:
    """Cria figura Plotly com tema escuro para uma série macro."""
    dates  = [r["date"]  for r in series_data]
    values = [r["value"] for r in series_data]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            name=name,
            line=dict(color="#22D3EE", width=1.5),
        )
    )
    fig.update_layout(
        title=_SERIES_TITLES.get(name, name),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,20,33,1)",
        font=dict(color="#94A3B8"),
        xaxis=dict(gridcolor="#1E2D42", showgrid=True),
        yaxis=dict(gridcolor="#1E2D42", showgrid=True),
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _chart_panel(name: str, series_data: list[dict]) -> None:
    """Render a chart inside a .panel wrapper with series title."""
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    if series_data:
        st.plotly_chart(_build_chart(name, series_data), use_container_width=True)
    else:
        series_title = _SERIES_TITLES.get(name, name)
        st.markdown(
            alert_block("warn",
                f"Dados indisponíveis — {series_title}",
                "Execute o pipeline de ingestão BCB para obter esta série."),
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _available_series() -> list[str]:
    """Return list of series keys that have data."""
    macro = get_macro_panel()
    return [k for k in _SERIES_ORDER if macro.get(k)]


def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header">
      <div class="page-header-title">Macro Motor</div>
      <div class="page-header-sub">Painel macroeconômico — Selic, PTAX, IPCA, CDS Brasil e regime de mercado</div>
    </div>
    """, unsafe_allow_html=True)

    macro = get_macro_panel()
    available = [k for k in _SERIES_ORDER if macro.get(k)]
    total = len(_SERIES_ORDER)

    # ── Macro data source status header (S06) ───────────────────────────────
    # Determine source health from data availability
    if not available:
        src_status = "EMPTY"
        src_label = "SEM DADOS MACRO"
        src_color = "neg"
    elif len(available) < total:
        src_status = "DEGRADED"
        src_label = f"PARCIAL — {len(available)}/{total} séries"
        src_color = "warn"
    else:
        src_status = "APPROVED_FOR_STUDY"
        src_label = "DADOS COMPLETOS — BCB"
        src_color = "pos"

    st.markdown(
        f'<div style="margin-bottom:16px; display:flex; align-items:center; gap:10px;">'
        f'{status_chip(src_status, label=src_label)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Alert: macro data unavailable ─────────────────────────────────────
    if not available:
        st.markdown(
            alert_block("error",
                "Dados macroeconômicos não disponíveis",
                "Verifique o pipeline de ingestão BCB. Selic, IPCA, PTAX, CDS e PIB não foram encontrados."),
            unsafe_allow_html=True,
        )
        st.stop()

    # ── Selic — full width (focal point) ─────────────────────────────────
    _chart_panel("selic", macro.get("selic", []))

    # ── IPCA + PTAX (row 2) ───────────────────────────────────────────────
    col_ipca, col_ptax = st.columns(2)
    with col_ipca:
        _chart_panel("ipca_12m", macro.get("ipca_12m", []))
    with col_ptax:
        _chart_panel("ptax", macro.get("ptax", []))

    # ── CDS + PIB (row 3) ─────────────────────────────────────────────────
    col_cds, col_pib = st.columns(2)
    with col_cds:
        _chart_panel("cds_brasil", macro.get("cds_brasil", []))
    with col_pib:
        _chart_panel("pib_nominal", macro.get("pib_nominal", []))


main()
