"""Oportunidades de Investimento — Phase 5 DEL-01."""
from __future__ import annotations

import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"     # Analista de Investimentos/12_PYTHON/

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

from _style import DARK_CSS
from src.dashboard.data import get_opportunities

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIGNAL_COLORS = {
    "DCF_DIVERGENCE":     "background-color:#3B82F6;color:white",
    "MOMENTUM_CROSSOVER": "background-color:#ca8a04;color:white",
    "IPE_EVENT":          "background-color:#1E3A5F;color:#93C5FD",
}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def main() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.title("Oportunidades de Investimento")

    opps = get_opportunities()

    if not opps:
        st.info("Nenhum sinal de oportunidade encontrado para hoje.")
        st.stop()

    for opp in opps:
        col1, col2, col3, col4 = st.columns([1, 3, 1, 2])

        with col1:
            st.markdown(f"**{opp['ticker']}**")

        with col2:
            st.write(opp["description"])

        with col3:
            signal_type = opp["signal_type"]
            badge_style = _SIGNAL_COLORS.get(signal_type, "background-color:#475569;color:white")
            st.markdown(
                f'<span style="{badge_style}; padding:2px 8px; border-radius:4px; '
                f'font-size:0.75rem">{signal_type}</span>',
                unsafe_allow_html=True,
            )

        with col4:
            score = opp.get("conviction_score", 0)
            st.progress(score / 100, text=f"{score}/100")

        st.markdown("---")


if __name__ == "__main__":
    main()

main()
