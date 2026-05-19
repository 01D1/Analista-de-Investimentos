"""Oportunidades de Investimento — Premium UI (Phase 5 DEL-01)."""
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
if _PIPELINE_ROOT in sys.path:
    sys.path.remove(_PIPELINE_ROOT)
sys.path.insert(0, _PIPELINE_ROOT)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    opportunity_card,
    section_title,
    empty_state,
)
from src.dashboard.data import get_opportunities


# ── Page ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(
        """
<div class="page-header">
  <div class="page-header-title">Top Oportunidades Quantitativas</div>
  <div class="page-header-sub">Sinais de alta convicção identificados pelo motor de inteligencia</div>
</div>""",
        unsafe_allow_html=True,
    )

    opps = get_opportunities()

    if not opps:
        empty_state("Nenhum sinal de oportunidade encontrado para hoje.", icon="")
        st.stop()

    # ── Conviction score threshold filter ────────────────────────────────────
    min_score = st.slider(
        "Conviction score minimo:",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        format="%d",
    )

    filtered = [o for o in opps if int(o.get("conviction_score") or 0) >= min_score]

    # ── Section title ─────────────────────────────────────────────────────────
    section_title(
        "{0} oportunidades com score >= {1}".format(len(filtered), min_score),
        icon="",
    )

    if not filtered:
        empty_state(
            "Nenhuma oportunidade com conviction score >= {0}.".format(min_score),
            icon="",
        )
        st.stop()

    # ── Cards grid (2 per row) ────────────────────────────────────────────────
    cards_per_row = 2
    for row_start in range(0, len(filtered), cards_per_row):
        chunk = filtered[row_start : row_start + cards_per_row]
        cols = st.columns(len(chunk))
        for col, opp in zip(cols, chunk):
            with col:
                st.markdown(
                    opportunity_card(
                        ticker=opp.get("ticker", "—"),
                        description=opp.get("description", ""),
                        signal_type=opp.get("signal_type", ""),
                        conviction_score=int(opp.get("conviction_score") or 0),
                    ),
                    unsafe_allow_html=True,
                )


main()
