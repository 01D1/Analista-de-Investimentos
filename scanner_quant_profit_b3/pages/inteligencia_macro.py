"""Painel Macroeconômico — Phase 5 DEL-01."""
from __future__ import annotations

import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"     # Analista de Investimentos/12_PYTHON/

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import plotly.graph_objects as go

from _style import DARK_CSS
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
            line=dict(color="#93C5FD", width=1.5),
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

def main() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.title("Painel Macroeconômico")

    macro = get_macro_panel()

    if not any(macro.values()):
        st.warning("Dados macroeconômicos não disponíveis. Verifique a ingestão BCB.")
        st.stop()

    # ── Selic — full width (focal point) ─────────────────────────────────
    selic_data = macro.get("selic", [])
    if selic_data:
        st.plotly_chart(_build_chart("selic", selic_data), use_container_width=True)
    else:
        st.caption(f"{_SERIES_TITLES['selic']}: dados não disponíveis")

    # ── IPCA + PTAX (row 2) ───────────────────────────────────────────────
    col_ipca, col_ptax = st.columns(2)
    with col_ipca:
        data = macro.get("ipca_12m", [])
        if data:
            st.plotly_chart(_build_chart("ipca_12m", data), use_container_width=True)
        else:
            st.caption(f"{_SERIES_TITLES['ipca_12m']}: dados não disponíveis")

    with col_ptax:
        data = macro.get("ptax", [])
        if data:
            st.plotly_chart(_build_chart("ptax", data), use_container_width=True)
        else:
            st.caption(f"{_SERIES_TITLES['ptax']}: dados não disponíveis")

    # ── CDS + PIB (row 3) ─────────────────────────────────────────────────
    col_cds, col_pib = st.columns(2)
    with col_cds:
        data = macro.get("cds_brasil", [])
        if data:
            st.plotly_chart(_build_chart("cds_brasil", data), use_container_width=True)
        else:
            st.caption(f"{_SERIES_TITLES['cds_brasil']}: dados não disponíveis")

    with col_pib:
        data = macro.get("pib_nominal", [])
        if data:
            st.plotly_chart(_build_chart("pib_nominal", data), use_container_width=True)
        else:
            st.caption(f"{_SERIES_TITLES['pib_nominal']}: dados não disponíveis")


if __name__ == "__main__":
    main()

main()
