"""Radar de Oportunidades — Home Operacional com motores reais de decisão.

Integra:
  - expected_value_engine   → EV score + assimetria + Kelly
  - signal_explainer        → gatilho em linguagem natural PT-BR
  - market_regime_engine    → regime macro/mercado
  - institutional_meta_score→ score de convicção multi-layer
  - cotahist_daily          → liquidez real (ADV 21d)
  - risk_snapshots          → risco estimado por ticker

Regras:
  - Nenhum cálculo novo de fair_value
  - Nenhuma escrita no banco
  - Nenhum mock — "indisponível" com motivo quando falta dado
  - Nenhuma referência a nomes de milestones ou caminhos internos
"""
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
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    section_title, empty_state, status_chip, alert_block, kpi_card,
)

# ── Import do payload real ────────────────────────────────────────────────────
try:
    from src.dashboard.radar_payload import get_radar_payload as _get_real_payload
    _HAS_PAYLOAD = True
except Exception as _e:
    _HAS_PAYLOAD = False
    _PAYLOAD_ERROR = str(_e)

# ── Fallback: payload legado (só scores básicos) ──────────────────────────────
try:
    from src.dashboard.data import get_opportunities as _get_legacy_opps
    _HAS_LEGACY = True
except Exception:
    _HAS_LEGACY = False


# ── Cache Streamlit ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _load_payload() -> dict:
    if _HAS_PAYLOAD:
        return _get_real_payload()
    return {}


# ── Helpers de renderização ───────────────────────────────────────────────────

def _score_color(score: float) -> str:
    if score >= 70:
        return "var(--pos-500)"
    if score >= 45:
        return "var(--warn-500)"
    return "var(--neg-500)"


def _tier_badge(tier: str, direction: str) -> str:
    tier = tier.upper()
    dir_colors = {
        "BUY":   ("var(--pos-tint)", "var(--pos-500)", "var(--pos-border)"),
        "WATCH": ("var(--warn-tint)", "var(--warn-500)", "var(--warn-border)"),
        "HOLD":  ("rgba(100,116,139,0.1)", "var(--fg-5)", "rgba(100,116,139,0.2)"),
        "SELL":  ("var(--neg-tint)", "var(--neg-500)", "var(--neg-border)"),
    }
    bg, fg, border = dir_colors.get(direction.upper(), dir_colors["HOLD"])
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'padding:2px 8px;border-radius:99px;border:1px solid {border};'
        f'background:{bg};font-size:.62rem;font-weight:800;color:{fg};">'
        f'Tier {tier}&nbsp;·&nbsp;{direction}</span>'
    )


def _action_chip(label: str, variant: str) -> str:
    colors = {
        "approved": ("var(--pos-tint)", "var(--pos-500)"),
        "monitor":  ("var(--warn-tint)", "var(--warn-500)"),
        "paper":    ("rgba(100,116,139,0.1)", "var(--fg-4)"),
        "blocked":  ("var(--neg-tint)", "var(--neg-500)"),
    }
    bg, fg = colors.get(variant, colors["paper"])
    return (
        f'<span style="padding:3px 10px;border-radius:99px;background:{bg};'
        f'color:{fg};font-size:.65rem;font-weight:700;">{label}</span>'
    )


def _metric_pill(label: str, value: str, available: bool = True) -> str:
    if not available:
        return (
            f'<span style="font-size:.6rem;color:var(--fg-6);">'
            f'{label}: <em style="color:var(--fg-7);">—</em></span>'
        )
    return (
        f'<span style="font-size:.6rem;color:var(--fg-5);">'
        f'{label}: <strong style="color:var(--fg-2);">{value}</strong></span>'
    )


def _render_regime_banner(payload: dict) -> None:
    """Banner compacto de regime macro + regime B3."""
    regime = payload.get("regime")
    b3 = payload.get("market_regime_b3", {})
    macro = payload.get("macro_overrides", {})

    # Regime macro global
    if regime:
        label = str(getattr(regime, "regime_label", "—")).replace("_", " ")
        tailwind = float(getattr(regime, "macro_tailwind", 50))
        risk_app = str(getattr(regime, "risk_appetite", "NEUTRAL")).upper()
        selic = macro.get("selic")
        ipca = macro.get("ipca")
        ptax_trend = macro.get("ptax_trend")

        if risk_app == "RISK_ON":
            risk_label = "RISK ON"
            bar_color = "var(--pos-500)"
        elif risk_app == "RISK_OFF":
            risk_label = "RISK OFF"
            bar_color = "var(--neg-500)"
        else:
            risk_label = "NEUTRO"
            bar_color = "var(--warn-500)"

        chip = status_chip("APPROVED_FOR_STUDY" if risk_app == "RISK_ON"
                           else ("BLOCKED" if risk_app == "RISK_OFF" else "MONITOR_ONLY"),
                           label=risk_label)

        selic_str = f"Selic {selic:.1f}%" if selic else "Selic —"
        ipca_str = f"IPCA {ipca:.1f}%" if ipca else ""
        ptax_str = f"PTAX {ptax_trend:+.1f}% 21d" if ptax_trend is not None else ""
        macro_pills = " · ".join(x for x in [selic_str, ipca_str, ptax_str] if x)

        st.markdown(f"""
        <div class="panel" style="padding:10px 16px;margin-bottom:14px;
             display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
          <span style="font-size:.6rem;font-weight:700;color:var(--fg-6);
                       text-transform:uppercase;letter-spacing:.8px;">Regime Macro</span>
          <span style="font-family:var(--font-mono);font-size:.8rem;font-weight:800;
                       color:var(--fg-1);">{label}</span>
          {chip}
          <div style="flex:1;min-width:80px;background:var(--bg-0);
                      border-radius:3px;height:4px;overflow:hidden;">
            <div style="width:{int(tailwind)}%;height:4px;
                        background:{bar_color};border-radius:3px;"></div>
          </div>
          <span style="font-family:var(--font-mono);font-size:.6rem;color:var(--fg-5);">
            Tailwind {tailwind:.0f} · {macro_pills}
          </span>
        </div>
        """, unsafe_allow_html=True)

    # Regime B3 (market_regime_daily)
    if b3.get("available"):
        primary = str(b3.get("primary_regime", "")).replace("_", " ")
        trend = str(b3.get("trend_regime", "")).replace("_", " ")
        vol = str(b3.get("volatility_regime", "")).replace("_", " ")
        liq = str(b3.get("liquidity_regime", "")).replace("_", " ")
        conf = float(b3.get("confidence", 0.5))
        date_str = str(b3.get("trade_date", ""))[:10]

        st.markdown(f"""
        <div class="panel" style="padding:8px 16px;margin-bottom:18px;
             display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
          <span style="font-size:.6rem;font-weight:700;color:var(--fg-6);
                       text-transform:uppercase;letter-spacing:.8px;">Mercado B3</span>
          <span style="font-family:var(--font-mono);font-size:.72rem;font-weight:700;
                       color:var(--fg-2);">{primary}</span>
          <span style="font-size:.6rem;color:var(--fg-5);">Tendência: <strong>{trend}</strong></span>
          <span style="font-size:.6rem;color:var(--fg-5);">Vol: <strong>{vol}</strong></span>
          <span style="font-size:.6rem;color:var(--fg-5);">Liquidez: <strong>{liq}</strong></span>
          <span style="font-family:var(--font-mono);font-size:.55rem;color:var(--fg-7);">
            conf {conf:.0%} · {date_str}
          </span>
        </div>
        """, unsafe_allow_html=True)


def _render_opportunity_card(opp: dict) -> None:
    """Renderiza cartão completo de uma oportunidade com todos os motores reais."""
    ticker   = opp.get("ticker", "—")
    score    = float(opp.get("score") or 0)
    direction = opp.get("direction", "HOLD")
    tier     = opp.get("tier", "D")
    tipo     = opp.get("tipo", "Ação")

    # Engine outputs
    gatilho   = str(opp.get("gatilho") or "monitorar")
    ev_score  = opp.get("ev_score")
    ev_summary = str(opp.get("ev_summary") or "")
    assimetria = str(opp.get("assimetria") or "—")
    liquidez  = str(opp.get("liquidez") or "—")
    risco_str = str(opp.get("risco") or "—")
    regime_ctx = str(opp.get("regime") or "—")
    upside    = opp.get("upside_pct")
    ev_avail  = bool(opp.get("ev_available"))
    kelly     = opp.get("kelly_fraction")
    warnings  = opp.get("warnings", [])
    driver    = str(opp.get("primary_driver") or "")
    realtime_exp = str(opp.get("realtime_explanation") or "")

    proxima_acao = str(opp.get("proxima_acao") or "Monitorar")
    acao_variant = str(opp.get("acao_variant") or "paper")
    scores   = opp.get("scores", {})
    bullish  = opp.get("top_bullish", [])
    bearish  = opp.get("top_bearish", [])

    score_color = _score_color(score)
    tier_html   = _tier_badge(tier, direction)
    acao_html   = _action_chip(proxima_acao, acao_variant)

    # Linha de sub-scores disponíveis
    sub_scores_pills = []
    if scores.get("momentum") is not None:
        sub_scores_pills.append(f"Mom: {scores['momentum']:.0f}")
    if scores.get("tendencia") is not None:
        sub_scores_pills.append(f"Tend: {scores['tendencia']:.0f}")
    if scores.get("liquidez") is not None:
        sub_scores_pills.append(f"Liq: {scores['liquidez']:.0f}")
    if scores.get("macro") is not None:
        sub_scores_pills.append(f"Macro: {scores['macro']:.0f}")
    sub_scores_str = " · ".join(sub_scores_pills) if sub_scores_pills else ""

    # EV pill
    ev_pill = ""
    if ev_avail and ev_score is not None:
        ev_color = _score_color(ev_score)
        ev_pill = (
            f'<span style="font-size:.6rem;background:var(--bg-2);padding:2px 8px;'
            f'border-radius:4px;font-family:var(--font-mono);">'
            f'EV <strong style="color:{ev_color};">{ev_score:.0f}</strong></span>'
        )

    # Kelly pill
    kelly_pill = ""
    if kelly and kelly >= 0.05:
        kelly_pill = (
            f'<span style="font-size:.6rem;background:var(--bg-2);padding:2px 8px;'
            f'border-radius:4px;font-family:var(--font-mono);">Kelly '
            f'<strong style="color:var(--pos-500);">{kelly:.0%}</strong></span>'
        )

    # Upside pill
    upside_pill = ""
    if upside is not None:
        up_color = "var(--pos-500)" if upside > 0 else "var(--neg-500)"
        upside_pill = (
            f'<span style="font-size:.6rem;background:var(--bg-2);padding:2px 8px;'
            f'border-radius:4px;font-family:var(--font-mono);">Upside '
            f'<strong style="color:{up_color};">{upside:+.1f}%</strong></span>'
        )

    # Fatores bullish/bearish como badges
    bullish_html = "".join(
        f'<span style="display:inline-block;background:var(--pos-tint);border:1px solid var(--pos-border);'
        f'border-radius:4px;padding:1px 7px;font-size:.58rem;color:var(--pos-500);margin:2px 3px 2px 0">{f}</span>'
        for f in bullish[:2]
    )
    bearish_html = "".join(
        f'<span style="display:inline-block;background:var(--neg-tint);border:1px solid var(--neg-border);'
        f'border-radius:4px;padding:1px 7px;font-size:.58rem;color:var(--neg-500);margin:2px 3px 2px 0">{f}</span>'
        for f in bearish[:2]
    )

    # Regime do ativo
    regime_pill = ""
    if regime_ctx and regime_ctx != "—" and regime_ctx != "indisponível":
        regime_pill = (
            f'<span style="font-size:.6rem;background:var(--bg-2);padding:2px 8px;'
            f'border-radius:4px;font-family:var(--font-mono);color:var(--fg-5);">Regime: '
            f'<strong style="color:var(--fg-2);">{regime_ctx}</strong></span>'
        )

    # Explicação (realtime > driver)
    exp_text = realtime_exp or (f"{driver}." if driver else "")
    exp_text = exp_text[:120]

    # Warnings (compacto)
    warn_html = ""
    if warnings:
        warn_html = (
            f'<div style="margin-top:6px;font-size:.56rem;color:var(--fg-7);'
            f'font-style:italic;">'
            + "; ".join(warnings[:2]) + '</div>'
        )

    st.markdown(f"""
    <div class="panel" style="padding:14px 18px;margin-bottom:10px;">
      <!-- Header: ticker + tier + score + ação -->
      <div style="display:flex;justify-content:space-between;
                  align-items:flex-start;gap:12px;flex-wrap:wrap;">
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
          <div style="font-family:var(--font-display);font-weight:900;
                      font-size:1.2rem;color:var(--fg-1);">{ticker}</div>
          <span style="font-family:var(--font-mono);font-size:.65rem;
                       color:var(--fg-5);background:var(--bg-2);
                       padding:2px 8px;border-radius:4px;">{tipo}</span>
          {tier_html}
        </div>
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
          <div style="text-align:center;">
            <div style="font-family:var(--font-display);font-weight:900;
                        font-size:1.6rem;color:{score_color};">{score:.0f}</div>
            <div style="font-family:var(--font-mono);font-size:.55rem;
                        color:var(--fg-6);">META SCORE</div>
          </div>
          {acao_html}
        </div>
      </div>

      <!-- Linha de gatilho (signal_explainer) -->
      <div style="margin-top:10px;padding:8px 12px;background:var(--bg-2);
                  border-radius:6px;border-left:3px solid var(--pos-border);">
        <span style="font-size:.6rem;font-weight:700;color:var(--fg-5);
                     text-transform:uppercase;letter-spacing:.6px;">Gatilho · </span>
        <span style="font-size:.72rem;color:var(--fg-1);">{gatilho}</span>
        {f'<div style="font-size:.62rem;color:var(--fg-5);margin-top:4px;">{driver}</div>' if driver else ""}
      </div>

      <!-- Pills de EV, Kelly, Upside, Regime -->
      <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
        {ev_pill} {kelly_pill} {upside_pill} {regime_pill}
      </div>

      <!-- Grade: Liquidez · Assimetria · Risco -->
      <div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr 1fr;
                  gap:8px;font-family:var(--font-mono);font-size:.62rem;">
        <div style="background:var(--bg-2);padding:6px 10px;border-radius:6px;">
          <div style="color:var(--fg-6);font-size:.55rem;margin-bottom:2px;">LIQUIDEZ (ADV 21d)</div>
          <div style="color:var(--fg-1);font-weight:700;">{liquidez}</div>
        </div>
        <div style="background:var(--bg-2);padding:6px 10px;border-radius:6px;">
          <div style="color:var(--fg-6);font-size:.55rem;margin-bottom:2px;">ASSIMETRIA (EV)</div>
          <div style="color:var(--fg-1);font-weight:700;">{assimetria}</div>
        </div>
        <div style="background:var(--bg-2);padding:6px 10px;border-radius:6px;">
          <div style="color:var(--fg-6);font-size:.55rem;margin-bottom:2px;">RISCO ESTIMADO</div>
          <div style="color:var(--fg-1);font-weight:700;">{risco_str}</div>
        </div>
      </div>

      <!-- EV summary e fatores -->
      {f'<div style="margin-top:8px;font-size:.62rem;font-family:var(--font-mono);color:var(--fg-5);">{ev_summary}</div>' if ev_summary else ""}

      <!-- Fatores bullish/bearish -->
      {f'<div style="margin-top:8px;">{bullish_html}{bearish_html}</div>' if bullish_html or bearish_html else ""}

      <!-- Sub-scores -->
      {f'<div style="margin-top:6px;font-size:.6rem;font-family:var(--font-mono);color:var(--fg-6);">{sub_scores_str}</div>' if sub_scores_str else ""}

      <!-- Explicação do sinal -->
      {f'<div style="margin-top:6px;font-size:.62rem;color:var(--fg-5);font-style:italic;">{exp_text}</div>' if exp_text else ""}

      {warn_html}
    </div>
    """, unsafe_allow_html=True)


def _render_integration_status(data_status: dict) -> None:
    """Painel de status de integração dos motores."""
    def _badge(val: str) -> str:
        v = str(val).lower()
        if v.startswith("integrado"):
            return f'<span style="color:var(--pos-500);font-weight:700;">✓ {val}</span>'
        if "indisponível" in v or "erro" in v:
            return f'<span style="color:var(--neg-500);font-weight:700;">✗ {val}</span>'
        return f'<span style="color:var(--warn-500);font-weight:700;">◐ {val}</span>'

    rows_html = ""
    for motor, status in data_status.items():
        motor_label = motor.replace("_", " ").title()
        rows_html += f"""
        <div style="display:flex;justify-content:space-between;padding:6px 10px;
                    border-bottom:1px solid var(--bg-2);font-size:.68rem;">
          <span style="color:var(--fg-3);">{motor_label}</span>
          <span>{_badge(status)}</span>
        </div>
        """

    with st.expander("Status de Integração dos Motores de Decisão", expanded=False):
        st.markdown(f"""
        <div class="panel" style="padding:0;">
          {rows_html}
        </div>
        """, unsafe_allow_html=True)


# ── Page principal ────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-title">Radar de Oportunidades</div>'
        '<div class="page-header-sub">'
        'Sinais de entrada ranqueados — expected value, liquidez, sinal técnico e regime macro'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Carregar payload ─────────────────────────────────────────────────────
    if not _HAS_PAYLOAD:
        st.error(f"Erro ao carregar motor de payload: {_PAYLOAD_ERROR if '_PAYLOAD_ERROR' in dir() else 'módulo indisponível'}")
        return

    with st.spinner("Carregando motores de decisão..."):
        payload = _load_payload()

    opportunities = payload.get("opportunities", [])
    data_status = payload.get("data_status", {})

    # ── Regime macro ─────────────────────────────────────────────────────────
    _render_regime_banner(payload)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total = len(opportunities)
    buys  = sum(1 for o in opportunities if o.get("direction") == "BUY")
    watch = sum(1 for o in opportunities if o.get("direction") == "WATCH")
    high_ev = sum(1 for o in opportunities if (o.get("ev_score") or 0) >= 60)
    with_adv = sum(1 for o in opportunities if o.get("liquidez_raw") is not None)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("SINAIS", str(total), color="cyan")
    with c2:
        kpi_card("BUY", str(buys), color="green")
    with c3:
        kpi_card("WATCH", str(watch), color="amber")
    with c4:
        kpi_card("EV ALTO (≥60)", str(high_ev), color="violet")
    with c5:
        kpi_card("COM ADV", str(with_adv), color="cyan")

    if not opportunities:
        st.markdown("<br>", unsafe_allow_html=True)
        empty_state(
            "Nenhum sinal identificado.\n"
            "O motor quantitativo precisa de dados de preço recentes (cotahist_daily) e "
            "snapshots de inteligência (asset_intelligence_snapshots) para gerar sinais.",
        )
        _render_integration_status(data_status)
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    cf1, cf2, cf3, cf4 = st.columns([1, 1, 1, 1])
    with cf1:
        min_score = st.slider("Meta score mínimo", 0, 100, 0, 5, key="ro_meta_score")
    with cf2:
        dirs_all = ["BUY", "WATCH", "HOLD", "SELL"]
        sel_dirs = st.multiselect("Direção", dirs_all, default=["BUY", "WATCH"], key="ro_dirs")
    with cf3:
        tiers_all = ["S", "A", "B", "C", "D"]
        sel_tiers = st.multiselect("Tier", tiers_all, default=tiers_all, key="ro_tiers")
    with cf4:
        only_ev = st.toggle("Apenas com EV calculado", value=False, key="ro_ev_only")

    filtered = [
        o for o in opportunities
        if float(o.get("score") or 0) >= min_score
        and (not sel_dirs or o.get("direction") in sel_dirs)
        and (not sel_tiers or o.get("tier") in sel_tiers)
        and (not only_ev or o.get("ev_available"))
    ]
    filtered.sort(key=lambda o: float(o.get("score") or 0), reverse=True)

    section_title(
        f"{len(filtered)} sinal(is) — score ≥ {min_score}"
        + (" · apenas com EV" if only_ev else ""),
        icon="",
    )

    if not filtered:
        empty_state(f"Nenhum sinal com os filtros selecionados.")
        _render_integration_status(data_status)
        return

    # ── Modo de visualização ─────────────────────────────────────────────────
    vm_col, rank_col = st.columns([2, 2])
    with vm_col:
        view_mode = st.radio(
            "Visualização", ["Cartões", "Ranking Compacto"],
            horizontal=True, key="ro_view_mode",
        )
    with rank_col:
        sort_by = st.selectbox(
            "Ordenar por",
            ["Meta Score", "EV Score", "Liquidez (ADV)", "Quant Score"],
            key="ro_sort",
        )

    # Resorting
    sort_keys = {
        "Meta Score":       lambda o: float(o.get("score") or 0),
        "EV Score":         lambda o: float(o.get("ev_score") or 0),
        "Liquidez (ADV)":   lambda o: float(o.get("liquidez_raw") or 0),
        "Quant Score":      lambda o: float(o.get("score_quant") or 0),
    }
    filtered.sort(key=sort_keys.get(sort_by, sort_keys["Meta Score"]), reverse=True)

    # ── Renderização ─────────────────────────────────────────────────────────
    if view_mode == "Cartões":
        for opp in filtered:
            _render_opportunity_card(opp)

    else:
        # Ranking compacto como tabela Streamlit
        import pandas as pd

        rows = []
        for o in filtered:
            rows.append({
                "Ticker":      o.get("ticker", "—"),
                "Tipo":        o.get("tipo", "—"),
                "Score":       o.get("score"),
                "Direção":     o.get("direction", "—"),
                "Tier":        o.get("tier", "—"),
                "EV Score":    o.get("ev_score"),
                "Assimetria":  o.get("assimetria", "—"),
                "Risco":       o.get("risco", "—"),
                "Liquidez":    o.get("liquidez", "—"),
                "Regime":      o.get("regime", "—"),
                "Gatilho":     str(o.get("gatilho") or "—")[:50],
                "Próx. Ação":  o.get("proxima_acao", "—"),
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score":    st.column_config.NumberColumn("Score", format="%.1f"),
                "EV Score": st.column_config.NumberColumn("EV Score", format="%.1f"),
            },
        )

    # ── Status de integração ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _render_integration_status(data_status)


main()
