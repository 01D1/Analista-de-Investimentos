"""Oportunidades — Scanner Institucional Probabilístico (Phase 4+)."""
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
    opportunity_card, section_title, empty_state,
    status_chip, alert_block, kpi_card,
)
from src.dashboard.data import get_opportunities

try:
    from src.quant.market_regime_engine import detect_regime
    from src.quant.signal_explainer import explain_html
    _HAS_META = True
except Exception:
    _HAS_META = False


# ── Tier / direction chips via status_chip (S05) ─────────────────────────────

_TIER_CHIP = {
    "S": ("chip chip-approved",       "Tier S"),
    "A": ("chip chip-approved",       "Tier A"),
    "B": ("chip chip-monitor",         "Tier B"),
    "C": ("chip chip-review",         "Tier C"),
    "D": ("chip chip-blocked",         "Tier D"),
}
_DIR_CHIP = {
    "BUY":   "chip chip-approved",
    "WATCH": "chip chip-monitor",
    "HOLD":  "chip chip-paper",
    "SELL":  "chip chip-blocked",
}


def _meta_badge(opp: dict) -> str:
    tier = opp.get("conviction_tier", "C")
    direction = opp.get("signal_direction", "WATCH")
    meta = float(opp.get("institutional_meta_score") or opp.get("conviction_score") or 0)
    tier_cls, tier_label = _TIER_CHIP.get(tier, ("chip chip-review", f"Tier {tier}"))
    dir_cls = _DIR_CHIP.get(direction, "chip chip-paper")
    tier_chip = status_chip(tier.upper(), label=tier_label) if tier.upper() in ("S", "A", "B", "C", "D") else f'<div class="{tier_cls}">{tier_label}</div>'
    dir_chip = status_chip(direction.upper(), label=direction)
    return (
        f'<div style="display:flex;gap:6px;align-items:center;margin-bottom:6px;">'
        f'{tier_chip}'
        f'{dir_chip}'
        f'<span style="font-size:1rem;font-weight:900;color:var(--brand-300);'
        f'font-family:\'Sora\',system-ui;margin-left:auto;">{meta:.0f}</span>'
        f'</div>'
    )


def _regime_banner(snapshot) -> None:
    if snapshot is None:
        return
    tailwind = float(getattr(snapshot, "macro_tailwind", 50))
    label = str(getattr(snapshot, "regime_label", "—")).replace("_", " ")
    risk_app = str(getattr(snapshot, "risk_appetite", "NEUTRAL")).upper()

    # Risk appetite chip
    if risk_app == "RISK_ON":
        risk_chip = status_chip("APPROVED_FOR_STUDY", label="RISK ON")
    elif risk_app == "RISK_OFF":
        risk_chip = status_chip("BLOCKED", label="RISK OFF")
    else:
        risk_chip = status_chip("MONITOR_ONLY", label="NEUTRAL")

    headwind = float(getattr(snapshot, "macro_headwind", 50))
    tail_str = f"Tailwind: {tailwind:.0f}"
    head_str = f"Headwind: {headwind:.0f}"

    st.markdown(f"""
    <div class="panel" style="margin-bottom:16px; padding:12px 16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:12px;">
            <span style="font-size:0.6rem;font-weight:700;color:var(--fg-6);text-transform:uppercase;letter-spacing:.8px;">Regime Macro</span>
            <span style="font-size:0.82rem;font-weight:800;color:var(--fg-1);font-family:var(--font-mono);">{label}</span>
            {risk_chip}
        </div>
        <div style="display:flex;gap:16px;font-size:0.72rem;color:var(--fg-5);margin-bottom:8px;font-family:var(--font-mono);">
            <span>Tailwind: <strong style="color:var(--pos-500);">{tailwind:.0f}</strong></span>
            <span>Headwind: <strong style="color:var(--neg-500);">{headwind:.0f}</strong></span>
        </div>
        <div style="background:var(--bg-0);border-radius:3px;height:4px;overflow:hidden;">
            <div style="width:{int(tailwind)}%;height:4px;background:linear-gradient(90deg,var(--brand-600),var(--pos-500));border-radius:3px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-title">Top Oportunidades Institucionais</div>'
        '<div class="page-header-sub">Scanner probabilístico multi-camada — '
        'distorções, expected value e fluxo institucional</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Regime macro no topo
    if _HAS_META:
        try:
            snapshot = detect_regime()
            _regime_banner(snapshot)
        except Exception:
            snapshot = None
    else:
        snapshot = None

    opps = get_opportunities()
    if not opps:
        empty_state("Nenhum sinal encontrado para hoje.")
        st.stop()

    # Filtros
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        min_score = st.slider("Score mínimo", 0, 100, 0, 5)
    with col_f2:
        tiers_all = ["S", "A", "B", "C", "D"]
        sel_tiers = st.multiselect("Tier", tiers_all, default=tiers_all)
    with col_f3:
        dirs_all = ["BUY", "WATCH", "HOLD", "SELL"]
        sel_dirs = st.multiselect("Direção", dirs_all, default=["BUY", "WATCH"])

    def _passes(o: dict) -> bool:
        meta = float(o.get("institutional_meta_score") or o.get("conviction_score") or 0)
        tier = o.get("conviction_tier", "C")
        direction = o.get("signal_direction", "WATCH")
        if meta < min_score:
            return False
        if sel_tiers and tier not in sel_tiers:
            return False
        if sel_dirs and direction not in sel_dirs:
            return False
        return True

    filtered = [o for o in opps if _passes(o)]
    # Ordenar por meta-score decrescente
    filtered.sort(
        key=lambda o: float(o.get("institutional_meta_score") or o.get("conviction_score") or 0),
        reverse=True,
    )

    section_title(f"{len(filtered)} oportunidade(s) — score >= {min_score}", icon="")

    if not filtered:
        empty_state(f"Nenhuma oportunidade com score >= {min_score}.")
        st.stop()

    # Cards 2x2
    for row_start in range(0, len(filtered), 2):
        chunk = filtered[row_start : row_start + 2]
        cols = st.columns(len(chunk))
        for col, opp in zip(cols, chunk):
            with col:
                meta_b = _meta_badge(opp)
                card_html = opportunity_card(
                    ticker=opp.get("ticker", "—"),
                    description=opp.get("description", ""),
                    signal_type=opp.get("signal_type", ""),
                    conviction_score=int(
                        float(opp.get("institutional_meta_score") or opp.get("conviction_score") or 0)
                    ),
                )
                # Injeta badges de tier/direction antes do card
                st.markdown(meta_b, unsafe_allow_html=True)
                st.markdown(card_html, unsafe_allow_html=True)

                # Detalhes expansíveis
                explanation = opp.get("explanation")
                if explanation and isinstance(explanation, dict):
                    with st.expander("Ver explicação institucional"):
                        st.markdown(explain_html(explanation), unsafe_allow_html=True)
                elif opp.get("top_bullish_factors") or opp.get("top_bearish_factors"):
                    with st.expander("Ver fatores"):
                        bulls = opp.get("top_bullish_factors", [])
                        bears = opp.get("top_bearish_factors", [])
                        if bulls:
                            st.caption("Favoráveis: " + " · ".join(bulls[:3]))
                        if bears:
                            st.caption("Riscos: " + " · ".join(bears[:3]))


main()
