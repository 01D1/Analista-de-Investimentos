"""Watchlist de Ativos — Phase 5 DEL-01/DEL-02."""
from __future__ import annotations

import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"     # Analista de Investimentos/12_PYTHON/

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import pandas as pd

from _style import DARK_CSS
from src.dashboard.data import get_watchlist_summary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POSITIONING_COLORS = {
    "COMPRAR": "background-color: #16a34a; color: white",
    "MANTER":  "background-color: #ca8a04; color: white",
    "VENDER":  "background-color: #dc2626; color: white",
}


def _color_positioning(val: str) -> str:
    return _POSITIONING_COLORS.get(val, "")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def main() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.title("Watchlist de Ativos")

    rows = get_watchlist_summary()

    if not rows:
        st.info(
            "Nenhuma tese gerada ainda. Execute: "
            "python -m src.main daemon para iniciar o pipeline."
        )
        st.stop()

    df = pd.DataFrame(rows)

    # ── Rename colunas para exibicao ──────────────────────────────────────
    rename_map = {
        "ticker":        "Ticker",
        "positioning":   "Posicionamento",
        "confidence":    "Confiança",
        "fair_value_brl": "Valor Justo (R$)",
        "upside_pct":    "Upside %",
        "price":         "Preço (R$)",
        "pe_ratio":      "P/E",
        "ev_ebitda":     "EV/EBITDA",
        "generated_at":  "Tese Gerada em",
    }
    # Mantém apenas colunas presentes no DataFrame
    cols_present = [c for c in rename_map if c in df.columns]
    df = df[cols_present].rename(columns=rename_map)

    # ── Formatação numérica ───────────────────────────────────────────────
    if "Valor Justo (R$)" in df.columns:
        df["Valor Justo (R$)"] = df["Valor Justo (R$)"].apply(
            lambda x: f"{x:.2f}" if x is not None else "—"
        )
    if "Upside %" in df.columns:
        df["Upside %"] = df["Upside %"].apply(
            lambda x: f"{x:+.1f}%" if x is not None else "—"
        )
    if "Preço (R$)" in df.columns:
        df["Preço (R$)"] = df["Preço (R$)"].apply(
            lambda x: f"{x:.2f}" if x is not None else "—"
        )

    # ── Styler com cores de posicionamento ────────────────────────────────
    styled = df.style.map(_color_positioning, subset=["Posicionamento"]) \
        if "Posicionamento" in df.columns else df.style

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Nota de atualização (DEL-02 freshness) ────────────────────────────
    last_thesis = rows[0].get("generated_at", "—")
    st.caption(
        f"Dados atualizados via cache (TTL 5 min). "
        f"Última tese: {last_thesis}"
    )


if __name__ == "__main__":
    main()

main()
