"""Watchlist de Ativos — Premium UI (Phase 5 DEL-01/DEL-02)."""
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
    watchlist_card,
    section_title,
    empty_state,
)
from src.dashboard.data import get_watchlist_summary


# ── Page ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(
        """
<div class="page-header">
  <div class="page-header-title">Watchlist de Ativos</div>
  <div class="page-header-sub">Visao consolidada de todos os ativos monitorados pela plataforma</div>
</div>""",
        unsafe_allow_html=True,
    )

    rows = get_watchlist_summary()

    if not rows:
        empty_state(
            "Nenhuma tese gerada ainda.\n"
            "Execute: python -m src.main daemon para iniciar o pipeline.",
            icon="",
        )
        st.stop()

    # ── Summary KPI header ───────────────────────────────────────────────────
    total   = len(rows)
    buy_n   = sum(1 for r in rows if str(r.get("positioning", "")).upper() == "COMPRAR")
    hold_n  = sum(1 for r in rows if str(r.get("positioning", "")).upper() == "MANTER")
    sell_n  = sum(1 for r in rows if str(r.get("positioning", "")).upper() == "VENDER")

    st.markdown(
        """
<div class="summary-header">
  <div class="summary-kpi">
    <div class="summary-kpi-num blue">{total}</div>
    <div class="summary-kpi-label">Total Ativos</div>
  </div>
  <div class="summary-kpi">
    <div class="summary-kpi-num green">{buy}</div>
    <div class="summary-kpi-label">COMPRAR</div>
  </div>
  <div class="summary-kpi">
    <div class="summary-kpi-num amber">{hold}</div>
    <div class="summary-kpi-label">MANTER</div>
  </div>
  <div class="summary-kpi">
    <div class="summary-kpi-num red">{sell}</div>
    <div class="summary-kpi-label">VENDER</div>
  </div>
</div>""".format(total=total, buy=buy_n, hold=hold_n, sell=sell_n),
        unsafe_allow_html=True,
    )

    # ── Filter & sort controls ────────────────────────────────────────────────
    col_search, col_pos, col_sort = st.columns([3, 2, 2])
    with col_search:
        search_val = st.text_input("Buscar ticker:", placeholder="ex: PETR4")
    with col_pos:
        pos_filter = st.selectbox(
            "Posicionamento:",
            options=["Todos", "COMPRAR", "MANTER", "VENDER"],
        )
    with col_sort:
        sort_by = st.selectbox(
            "Ordenar por:",
            options=["Ticker", "Upside %", "Valor Justo"],
        )

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = rows

    if search_val:
        q = search_val.strip().upper()
        filtered = [r for r in filtered if q in str(r.get("ticker", "")).upper()]

    if pos_filter != "Todos":
        filtered = [r for r in filtered
                    if str(r.get("positioning", "")).upper() == pos_filter.upper()]

    # ── Sort ──────────────────────────────────────────────────────────────────
    def _safe_float(val, default=0.0) -> float:
        try:
            return float(val or default)
        except (TypeError, ValueError):
            return default

    if sort_by == "Upside %":
        filtered = sorted(
            filtered,
            key=lambda r: _safe_float(r.get("upside_pct"), -9999),
            reverse=True,
        )
    elif sort_by == "Valor Justo":
        filtered = sorted(
            filtered,
            key=lambda r: _safe_float(r.get("fair_value_brl"), 0),
            reverse=True,
        )
    else:
        filtered = sorted(filtered, key=lambda r: str(r.get("ticker", "")))

    # ── Cards grid ────────────────────────────────────────────────────────────
    section_title("{0} ativos encontrados".format(len(filtered)), icon="")

    if not filtered:
        empty_state("Nenhum ativo corresponde ao filtro.", icon="")
    else:
        # Build cards in groups of 3 per row
        cards_per_row = 3
        for row_start in range(0, len(filtered), cards_per_row):
            chunk = filtered[row_start : row_start + cards_per_row]
            cols = st.columns(len(chunk))
            for col, asset_row in zip(cols, chunk):
                with col:
                    st.markdown(
                        watchlist_card(asset_row),
                        unsafe_allow_html=True,
                    )

    # ── Freshness note ────────────────────────────────────────────────────────
    last_thesis = rows[0].get("generated_at", "—") if rows else "—"
    st.caption(
        "Dados em cache (TTL 5 min). Ultima tese gerada: {0}".format(last_thesis)
    )


main()
