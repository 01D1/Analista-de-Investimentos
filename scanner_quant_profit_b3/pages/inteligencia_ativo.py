"""Análise de Ativo — Phase 5 DEL-01/DEL-05."""
from __future__ import annotations

import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# pipeline root must precede scanner root so data.py gets src.utils.logger (pipeline pkg)
_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
if _PIPELINE_ROOT in sys.path:
    sys.path.remove(_PIPELINE_ROOT)
sys.path.insert(0, _PIPELINE_ROOT)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st

from _style import DARK_CSS
from src.data_quality.ri_sites import get_valid_ri_url_for_ticker
from src.dashboard.data import get_watchlist_summary, get_asset_detail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BADGE_COLORS = {
    "HIGH":   "background-color:#dc2626;color:white",
    "MEDIUM": "background-color:#ca8a04;color:white",
    "LOW":    "background-color:#16a34a;color:white",
}


def _impact_badge(level: str) -> str:
    return _BADGE_COLORS.get(level, "background-color:#475569;color:white")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def main() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.title("Análise de Ativo")

    # ── Ticker selector ───────────────────────────────────────────────────
    rows = get_watchlist_summary()
    if not rows:
        st.info(
            "Nenhuma tese gerada ainda. Execute: "
            "python -m src.main daemon para iniciar o pipeline."
        )
        st.stop()

    tickers = sorted(set(r["ticker"] for r in rows))
    ticker = st.selectbox("Selecionar ativo:", tickers)

    detail = get_asset_detail(ticker)
    if detail is None:
        st.info(
            f"Sem dados para {ticker}. Execute o pipeline para gerar a tese de investimento."
        )
        st.stop()

    thesis = detail["thesis"]  # already deserialized dict in data.py

    # ── Metric row ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Posicionamento", thesis.get("positioning", "—"))
    with col2:
        fair_value = thesis.get("fair_value_brl", 0)
        st.metric("Valor Justo (R$)", f"R$ {fair_value:.2f}")
    with col3:
        upside = detail.get("dcf", {}).get("upside_pct")
        st.metric("Upside", f"{upside:+.1f}%" if upside is not None else "—")

    ri_url = get_valid_ri_url_for_ticker(ticker)
    if ri_url:
        st.link_button("Site de RI", ri_url)
    else:
        st.caption("RI pendente de validação")

    # ── Bull / Bear cases ─────────────────────────────────────────────────
    st.subheader("Cenário Otimista")
    st.write(thesis.get("bull_case", "—"))   # CR-02: st.write avoids HTML rendering of LLM content

    st.subheader("Cenário Pessimista")
    st.write(thesis.get("bear_case", "—"))   # CR-02: st.write avoids HTML rendering of LLM content

    # ── Drivers ───────────────────────────────────────────────────────────
    st.subheader("Drivers de Investimento")
    drivers = thesis.get("drivers", [])
    if drivers:
        for d in drivers:
            with st.expander(f"Driver: {d.get('title', '—')}", expanded=False):
                st.write(d.get("description", ""))
                impact = d.get("impact", "")
                if impact:
                    st.markdown(
                        f'<span style="{_impact_badge(impact)}; '
                        f'padding:2px 8px; border-radius:4px">{impact}</span>',
                        unsafe_allow_html=True,
                    )
    else:
        st.caption("Nenhum driver disponível.")

    # ── Risks ─────────────────────────────────────────────────────────────
    st.subheader("Riscos")
    risks = thesis.get("risks", [])
    if risks:
        for d in risks:
            with st.expander(f"Risco: {d.get('title', '—')}", expanded=False):
                st.write(d.get("description", ""))
                severity = d.get("severity", "")
                if severity:
                    st.markdown(
                        f'<span style="{_impact_badge(severity)}; '
                        f'padding:2px 8px; border-radius:4px">{severity}</span>',
                        unsafe_allow_html=True,
                    )
    else:
        st.caption("Nenhum risco disponível.")

    # ── PDF download (DEL-05) ─────────────────────────────────────────────
    try:
        from src.delivery.pdf_report import ReportGenerator
        pdf_bytes = ReportGenerator().generate(ticker, detail)
        st.download_button(
            label="Baixar Relatório PDF",
            data=pdf_bytes,
            file_name=f"relatorio_{ticker}.pdf",
            mime="application/pdf",
        )
    except Exception:
        st.error(
            "Não foi possível gerar o relatório. "
            "Tente novamente ou contate o administrador."
        )

    # ── Freshness ─────────────────────────────────────────────────────────
    generated_at = detail.get("generated_at", "—")
    st.caption(f"Atualizado em: {generated_at}")


main()
