"""Radar AI — Painel de Inteligencia Integrada por Ativo.

Fontes reais (S02):
  - src.dashboard.data.get_watchlist_summary()
  - src.dashboard.data.get_opportunities()
  - src.dashboard.data.get_asset_detail()
  - src.dashboard.data.get_risk_snapshots()
  - src.integration.asset_intelligence_store.load_latest_asset_intelligence_snapshot()
  - src.integration.asset_intelligence_model ASSET_INTELLIGENCE_COLUMNS

Regras:
  - Nenhum mock ou dado hardcoded.
  - Nenhuma chamada a APIs externas / LLM.
  - Nenhum shell vazio (panel-shell com conteudo real ou empty_state).
  - Nao depende de radar_macro_os.
  - empty states honestos quando nao houver dados.
  - MONITOR_ONLY NAO vira APPROVED.
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
if _PIPELINE_ROOT in sys.path:
    sys.path.remove(_PIPELINE_ROOT)
# Avoid polluting src namespace with pipeline modules
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)

for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    section_title,
    kpi_card,
    kpi_strip,
    empty_state,
    alert_block,
    status_chip,
    score_bar,
    positioning_badge,
    watchlist_card,
)
from src.dashboard.data import (
    get_watchlist_summary,
    get_opportunities,
    get_asset_detail,
    get_risk_snapshots,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_float(v, decimals=2) -> str:
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"

def _upside_color(pct: float) -> str:
    if pct is None:
        return "var(--fg-5)"
    if pct > 20:
        return "var(--pos-500)"
    if pct > 0:
        return "var(--warn-500)"
    return "var(--neg-500)"

def _positioning_color(pos: str) -> str:
    pos = str(pos or "").upper()
    if pos == "COMPRAR":
        return "var(--pos-500)"
    if pos == "VENDER":
        return "var(--neg-500)"
    return "var(--fg-4)"

def _regime_chip(status: str, label: str | None = None) -> str:
    """Render governance/data quality chip via status_chip."""
    s = str(status or "").strip()
    return status_chip(s, label=label)

def _conviction_tier(status: str) -> tuple[str, str]:
    """Map integrated_status to conviction tier label."""
    if not status:
        return "D", "D"
    s = str(status).upper()
    if "ALTA_CONVERGENCIA" in s:
        return "A", "CONVICCÃO ALTA"
    if "ASSIMETRIA" in s:
        return "B", "ASSIMETRIA"
    if "APENAS_MONITORAR" in s:
        return "D", "MONITORAR"
    if "BLOQUEADO" in s or "DIVERGENCIA" in s:
        return "C", "DIVERGÊNCIA"
    return "D", "—"

def _data_source_label(val_source: str) -> str:
    """Human-readable source label."""
    mapping = {
        "pipeline_bridge": "Pipeline DCF",
        "scanner_quant_db": "Scanner DB",
        "none": "Sem dados",
    }
    return mapping.get(str(val_source).lower(), str(val_source))


# ── Tab definitions ───────────────────────────────────────────────────────────

_TABS = ["Visao Geral", "Oportunidades", "Tese Detalhada", "Risco", "Gestao"]

_TAB_ICONS = {
    "Visao Geral":        "",
    "Oportunidades":      "",
    "Tese Detalhada":      "",
    "Risco":              "",
    "Gestao":             "",
}


# ── Tab: Visao Geral ──────────────────────────────────────────────────────────

def render_overview_tab(rows: list[dict]) -> None:
    """Lista de todos os ativos com posicionamento e scores."""
    if not rows:
        empty_state(
            "Nenhum ativo registrado.\n"
            "Execute o pipeline de inteligencia para populer o radar.",
            icon="",
        )
        return

    # KPIs de aggregate
    total = len(rows)
    comprar = sum(1 for r in rows if str(r.get("positioning", "")).upper() == "COMPRAR")
    vender  = sum(1 for r in rows if str(r.get("positioning", "")).upper() == "VENDER")
    manter  = total - comprar - vender

    # Coverage — tickers com valuation vs sem
    val_cov = sum(1 for r in rows if r.get("valuation_available", False))
    has_val_pct = int(round(val_cov / total * 100)) if total else 0

    kpi_strip([
        {"label": "Ativos",     "value": str(total),    "color": "cyan"},
        {"label": "Comprar",   "value": str(comprar),  "color": "pos"},
        {"label": "Vender",     "value": str(vender),   "color": "neg"},
        {"label": "Valuation", "value": f"{has_val_pct}%", "color": "violet"},
    ])

    section_title("Ativos Monitorados", icon="")

    for row in rows:
        # Extract valuation source label for subtitle
        val_src = _data_source_label(row.get("valuation_source", ""))
        sub_label = f"Score {row.get('confidence', 'N/D')} · {val_src}" if val_src != "none" else f"Score {row.get('confidence', 'N/D')}"
        st.markdown(watchlist_card(row), unsafe_allow_html=True)


# ── Tab: Oportunidades ────────────────────────────────────────────────────────

def render_opportunities_tab() -> None:
    """Top opcoes ordenadas por conviction score real."""
    opportunities = get_opportunities()
    if not opportunities:
        empty_state(
            "Nenhuma oportunidade com score positivo.\n"
            "O pipeline ainda nao executou ou nenhum ativo atingiu o limiar.",
            icon="",
        )
        return

    section_title("Top Oportunidades por Score", icon="")

    for opp in opportunities:
        tier_label = _conviction_tier(opp.get("signal_type", ""))[1]
        score = int(opp.get("conviction_score") or 0)
        direction = str(opp.get("signal_direction", "HOLD")).upper()

        # Upside from valuation if available
        upside = opp.get("upside_pct")

        # Build opportunity card content
        score_color = "var(--pos-500)" if direction == "BUY" else (
            "var(--neg-500)" if direction == "SELL" else "var(--warn-500)"
        )

        st.markdown(f"""
        <div style="
            background: var(--bg-3);
            border: 1px solid var(--border-1);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
            animation: fadeInUp 0.35s ease;
        ">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                <div>
                    <div style="font-family:var(--font-display); font-size:1.3rem; font-weight:900;
                         color:var(--fg-1); letter-spacing:-0.3px;">
                        {opp.get('ticker', '—')}
                    </div>
                    <div style="font-size:.65rem; color:var(--fg-5); margin-top:3px; font-family:var(--font-mono);">
                        {tier_label} · {opp.get('signal_type', '—')}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:var(--font-display); font-weight:900; font-size:1.6rem;
                         color:{score_color};">{score}</div>
                    <div style="font-family:var(--font-mono); font-size:.62rem; color:var(--fg-5);">
                        {direction}
                    </div>
                </div>
            </div>
            <div style="font-size:.78rem; color:var(--fg-3); line-height:1.5; margin-bottom:10px;">
                {opp.get('description', 'Sem sinal concreto ainda. Pipeline pendente.')}
            </div>
            <!-- Sub-scores -->
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:4px;">Tecnico</div>
                    <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--fg-2);">
                        {_fmt_float(opp.get('technical_score_final'), 0)}
                    </div>
                </div>
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:4px;">Quant</div>
                    <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--fg-2);">
                        {_fmt_float(opp.get('quant_score'), 0)}
                    </div>
                </div>
                <div style="background:var(--bg-0); border-radius:8px; padding:8px; text-align:center;">
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:4px;">Upside</div>
                    <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700;
                         color:{_upside_color(upside)};">
                        {_fmt_float(upside, 0)}%
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Tab: Tese Detalhada ───────────────────────────────────────────────────────

def render_thesis_tab(tickers: list[str]) -> None:
    """Ticker selector + thesis detalhada com todos os componentes."""
    if not tickers:
        empty_state("Nenhum ativo disponivel.", icon="")
        return

    ticker = st.selectbox("Selecionar ativo para ver a tese:", tickers, key="thesis_ticker")

    detail = get_asset_detail(ticker)
    if detail is None:
        empty_state(
            f"Sem dados para {ticker}. "
            "Execute o pipeline para gerar a tese.",
            icon="",
        )
        return

    thesis = detail.get("thesis", {})
    positioning = str(thesis.get("positioning", "MANTER")).upper()
    integrated_score = float(detail.get("integrated_score") or 0)
    integrated_conf = str(detail.get("integrated_confidence") or "")
    integrated_status = str(detail.get("integrated_status") or "SEM_DADOS")
    gov_status = str(detail.get("integrated_governance_status") or "")

    # ── Hero com posicionamento e score ────────────────────────────────────
    pos_color = _positioning_color(positioning)
    upside_pct = detail.get("upside_pct")
    upside_label = f"+{upside_pct:.1f}%" if upside_pct is not None else ""

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, var(--bg-2) 0%, var(--bg-3) 60%, var(--bg-elevated) 100%);
        border: 1px solid var(--border-1); border-radius: 16px;
        padding: 20px 24px; margin-bottom: 18px; position: relative; overflow: hidden;
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="font-family:var(--font-display); font-size:1.6rem; font-weight:900;
                     color:var(--fg-1); margin-bottom:2px;">{ticker}</div>
                <div style="color:var(--fg-4); font-size:.8rem;">Score {_fmt_float(integrated_score, 0)}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:var(--font-display); font-weight:900; font-size:1.6rem;
                     color:{pos_color};">{positioning}</div>
                <div style="font-family:var(--font-mono); font-size:.72rem; color:var(--fg-5);">
                    {upside_label}
                </div>
            </div>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
            <span style="background:var(--bg-0); border:1px solid var(--border-1);
                 border-radius:6px; padding:3px 8px; font-family:var(--font-mono);
                 font-size:.6rem; color:var(--fg-5);">
                {integrated_conf or integrated_status}
            </span>
            {f'<span style="background:var(--warn-tint); border:1px solid var(--warn-border); '
             f'border-radius:6px; padding:3px 8px; font-family:var(--font-mono); '
             f'font-size:.6rem; color:var(--warn-500);">MONITORAR</span>' if 'MONITOR' in integrated_status.upper() else ''}
            {f'<span style="background:var(--neg-tint); border:1px solid var(--neg-border); '
             f'border-radius:6px; padding:3px 8px; font-family:var(--font-mono); '
             f'font-size:.6rem; color:var(--neg-500);">BLOQUEADO</span>' if 'BLOQUEADO' in integrated_status.upper() else ''}
            {f'<span style="background:var(--pos-tint); border:1px solid var(--pos-border); '
             f'border-radius:6px; padding:3px 8px; font-family:var(--font-mono); '
             f'font-size:.6rem; color:var(--pos-500);">APROVADO</span>' if 'ALTA_CONVERGENCIA' in integrated_status.upper() else ''}
            {_regime_chip(gov_status, label="GOVERNAMCA") if gov_status else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Valuation section ──────────────────────────────────────────────────
    val_avail = detail.get("valuation_available", False)
    val_src = _data_source_label(detail.get("valuation_source", "none"))
    val_method = str(detail.get("valuation_method", "") or "")
    val_date = str(detail.get("valuation_date", "") or "")
    fair_val = detail.get("fair_value")
    market_price = detail.get("market_price") or detail.get("current_price")

    if val_avail and fair_val:
        upside_val = detail.get("upside_pct")
        upside_color = _upside_color(upside_val)
        upside_label = f"{upside_val:+.1f}%" if upside_val is not None else ""

        st.markdown(f"""
        <div style="
            background: var(--bg-3); border: 1px solid var(--border-1);
            border-radius: 14px; padding: 16px 18px; margin-bottom: 14px;
        ">
            <div style="font-size:.65rem; text-transform:uppercase; letter-spacing:.8px;
                 color:var(--fg-5); font-weight:700; margin-bottom:12px;">VALUATION</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:12px;">
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:4px;">Preco Atual</div>
                    <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:700; color:var(--fg-1);">
                        R$ {_fmt_float(market_price)}
                    </div>
                </div>
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:4px;">Valor Justo</div>
                    <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:700; color:var(--fg-1);">
                        R$ {_fmt_float(fair_val)}
                    </div>
                </div>
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:4px;">Upside</div>
                    <div style="font-family:var(--font-mono); font-size:1.1rem; font-weight:700; color:{upside_color};">
                        {upside_label}
                    </div>
                </div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; font-size:.62rem; font-family:var(--font-mono); color:var(--fg-5);">
                <span style="background:var(--bg-0); border:1px solid var(--border-1);
                     border-radius:5px; padding:2px 7px;">{val_src}</span>
                {f'<span style="background:var(--bg-0); border:1px solid var(--border-1); '
                 f'border-radius:5px; padding:2px 7px;">{val_method}</span>' if val_method else ''}
                {f'<span style="background:var(--bg-0); border:1px solid var(--border-1); '
                 f'border-radius:5px; padding:2px 7px;">{val_date}</span>' if val_date else ''}
            </div>
            <!-- Upside bar -->
            {f'''<div style="margin-top:10px;">
                <div style="background:var(--bg-0); border-radius:99px; height:4px; overflow:hidden;">
                    <div style="width:{min(abs(upside_val or 0) * 2, 100)}%; height:100%;
                         background:{upside_color}; border-radius:99px;"></div>
                </div>
            </div>''' if upside_val else ''}
        </div>
        """, unsafe_allow_html=True)
    else:
        empty_state(
            f"Valuation nao disponivel para {ticker}.\n"
            "O pipeline DCF ainda nao executou para este ativo.",
            icon="",
        )

    # ── Scores detalhados ──────────────────────────────────────────────────
    section_title("Scores por Dimensão", icon="")
    tech_score = detail.get("technical_score_final")
    quant_sc = detail.get("quant_score")
    fq_score = detail.get("fundamental_quality_score")
    data_q = detail.get("data_quality_score")

    for label, score in [
        ("Tecnico", tech_score),
        ("Quantitativo", quant_sc),
        ("Qualidade Fundamental", fq_score),
        ("Qualidade de Dados", data_q),
    ]:
        if score is not None:
            try:
                val = float(score)
                color = "var(--brand-500)" if val >= 60 else "var(--warn-500)" if val >= 40 else "var(--neg-500)"
                st.markdown(score_bar(label, val, color=color), unsafe_allow_html=True)
            except (TypeError, ValueError):
                pass

    # ── Bull / Bear cases ───────────────────────────────────────────────────
    st.markdown("""
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:4px;">
    """, unsafe_allow_html=True)

    bull = thesis.get("bull_case", "—")
    bear = thesis.get("bear_case", "—")
    drivers = thesis.get("drivers", [])
    risks   = thesis.get("risks", [])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="background:var(--pos-tint); border:1px solid var(--pos-border);
             border-radius:12px; padding:14px 16px;">
            <div style="font-size:.65rem; text-transform:uppercase; letter-spacing:.8px;
                 color:var(--pos-500); font-weight:700; margin-bottom:8px;">BULL CASE</div>
            <div style="font-size:.8rem; color:var(--fg-3); line-height:1.5;">
        """, unsafe_allow_html=True)
        st.markdown(bull)
        if drivers:
            st.markdown("</div><div style='margin-top:10px;'>", unsafe_allow_html=True)
            for d in drivers:
                st.markdown(f"""
                <div style="display:flex; gap:8px; padding:5px 0; border-bottom:1px solid var(--pos-border);">
                    <span style="font-size:.72rem; color:var(--pos-500); font-weight:700;">▸</span>
                    <span style="font-size:.75rem; color:var(--fg-3);">{d.get('title', '—')}</span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background:var(--neg-tint); border:1px solid var(--neg-border);
             border-radius:12px; padding:14px 16px;">
            <div style="font-size:.65rem; text-transform:uppercase; letter-spacing:.8px;
                 color:var(--neg-500); font-weight:700; margin-bottom:8px;">BEAR CASE</div>
            <div style="font-size:.8rem; color:var(--fg-3); line-height:1.5;">
        """, unsafe_allow_html=True)
        st.markdown(bear)
        if risks:
            st.markdown("</div><div style='margin-top:10px;'>", unsafe_allow_html=True)
            for r in risks:
                sev = str(r.get("severity", "MEDIUM")).upper()
                sev_color = "var(--neg-500)" if sev == "HIGH" else "var(--warn-500)"
                st.markdown(f"""
                <div style="display:flex; gap:8px; padding:5px 0; border-bottom:1px solid var(--neg-border);">
                    <span style="font-size:.72rem; color:{sev_color}; font-weight:700;">▸</span>
                    <span style="font-size:.75rem; color:var(--fg-3);">{r.get('title', '—')}</span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Tab: Risco ────────────────────────────────────────────────────────────────

def render_risk_tab(tickers: list[str]) -> None:
    """Risk snapshots para tickers selecionados."""
    if not tickers:
        empty_state("Nenhum ativo disponivel.", icon="")
        return

    selected = st.multiselect(
        "Selecionar ativos para analisar risco:",
        sorted(tickers),
        default=sorted(tickers[:5]),
        key="risk_tickers",
    )

    if not selected:
        empty_state("Selecione ao menos um ativo.", icon="")
        return

    snapshots = get_risk_snapshots(tickers=selected)
    if not snapshots:
        empty_state(
            f"Nenhum snapshot de risco para {', '.join(selected)}.\n"
            "Execute o pipeline de risco para gerar os calculos.",
            icon="",
        )
        return

    for snap in snapshots:
        ticker = snap.get("ticker", "—")
        risk_status = str(snap.get("risk_status", "")).upper()
        risk_color = ("var(--neg-500)" if risk_status in ("ALTO", "CRITICO") else
                       "var(--warn-500)" if risk_status == "MEDIO" else "var(--fg-4)")

        var95 = snap.get("var_95")
        es95 = snap.get("expected_shortfall_95")
        vol  = snap.get("ensemble_vol")
        lim_factor = snap.get("limiting_factor", "—")
        explanation = snap.get("explanation", "—")
        created = snap.get("created_at", "—")

        st.markdown(f"""
        <div style="
            background: var(--bg-3); border: 1px solid var(--border-1);
            border-radius: 14px; padding: 16px 18px; margin-bottom: 12px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <div style="font-family:var(--font-display); font-size:1.2rem; font-weight:900; color:var(--fg-1);">
                    {ticker}
                </div>
                <div style="
                    background:var(--neg-tint); border:1px solid var(--neg-border);
                    border-radius:6px; padding:3px 9px;
                    font-family:var(--font-mono); font-size:.65rem; font-weight:800;
                    color:{risk_color};">{risk_status or 'N/D'}</div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:10px;">
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:3px;">VaR 95%</div>
                    <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--fg-1);">
                        {_fmt_float(var95, 1)}%
                    </div>
                </div>
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:3px;">ES 95%</div>
                    <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--fg-1);">
                        {_fmt_float(es95, 1)}%
                    </div>
                </div>
                <div>
                    <div style="font-size:.58rem; color:var(--fg-6); text-transform:uppercase;
                         letter-spacing:.5px; margin-bottom:3px;">Volatilidade</div>
                    <div style="font-family:var(--font-mono); font-size:.9rem; font-weight:700; color:var(--fg-1);">
                        {_fmt_float(vol, 1)}%
                    </div>
                </div>
            </div>
            <div style="font-size:.72rem; color:var(--fg-4); margin-bottom:6px;">
                <strong style="color:var(--fg-5);">Fator limitante:</strong> {lim_factor}
            </div>
            <div style="font-size:.78rem; color:var(--fg-4); line-height:1.4; margin-bottom:8px;">
                {explanation}
            </div>
            <div style="font-size:.58rem; color:var(--fg-6); font-family:var(--font-mono);">
                Atualizado: {created}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Tab: Gestao ───────────────────────────────────────────────────────────────

def render_governance_tab(rows: list[dict]) -> None:
    """Governanca: tickers bloqueados, monitorar, qualidade de dados."""
    if not rows:
        empty_state("Nenhum ativo registrado.", icon="")
        return

    blocked   = [r for r in rows if "BLOQUEADO" in str(r.get("positioning", "")).upper()]
    monitor   = [r for r in rows if str(r.get("confidence", "")).upper() in ("MONITORAR", "APENAS_MONITORAR")]
    approved  = [r for r in rows if str(r.get("positioning", "")).upper() == "COMPRAR"]

    kpi_strip([
        {"label": "Bloqueados",  "value": str(len(blocked)),   "color": "neg"},
        {"label": "Monitorar",   "value": str(len(monitor)),   "color": "warn"},
        {"label": "Aprovados",   "value": str(len(approved)),  "color": "pos"},
        {"label": "Total",       "value": str(len(rows)),      "color": "cyan"},
    ])

    # Bloqueados
    if blocked:
        section_title("Bloqueados por Governanca", icon="")
        for r in blocked:
            st.markdown(f"""
            <div style="background:var(--neg-tint); border:1px solid var(--neg-border);
                 border-radius:12px; padding:12px 16px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-family:var(--font-display); font-size:1.1rem; font-weight:900; color:var(--fg-1);">
                        {r.get('ticker', '—')}
                    </span>
                    <span style="background:var(--neg-tint); border:1px solid var(--neg-border);
                         border-radius:5px; padding:2px 8px; font-family:var(--font-mono);
                         font-size:.62rem; font-weight:800; color:var(--neg-500);">BLOQUEADO</span>
                </div>
                <div style="font-size:.75rem; color:var(--fg-4); margin-top:6px;">
                    {r.get('confidence', 'Sem motivo especifico.')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Monitorar
    if monitor:
        section_title("Monitorar", icon="")
        for r in monitor:
            st.markdown(f"""
            <div style="background:var(--warn-tint); border:1px solid var(--warn-border);
                 border-radius:12px; padding:12px 16px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-family:var(--font-display); font-size:1.1rem; font-weight:900; color:var(--fg-1);">
                        {r.get('ticker', '—')}
                    </span>
                    <span style="background:var(--warn-tint); border:1px solid var(--warn-border);
                         border-radius:5px; padding:2px 8px; font-family:var(--font-mono);
                         font-size:.62rem; font-weight:800; color:var(--warn-500);">MONITORAR</span>
                </div>
                <div style="font-size:.75rem; color:var(--fg-4); margin-top:6px;">
                    {r.get('confidence', 'Estrutura valida, requer validacao continua.')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if not blocked and not monitor:
        st.markdown(alert_block(
            "info",
            "Governanca OK",
            "Nenhum ativo bloqueado ou em monitoramento. "
            "Todos os ativos com dados suficientes estao em estado normal.",
        ), unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
        <div class="page-header-title">Radar AI</div>
        <div class="page-header-sub">Inteligencia integrada — score, tese e gestao de risco por ativo</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    rows = get_watchlist_summary()
    tickers = sorted(set(r["ticker"] for r in rows)) if rows else []

    # ── Tab navigation ────────────────────────────────────────────────────────
    tabs = st.tabs(_TABS)

    with tabs[0]:
        render_overview_tab(rows)

    with tabs[1]:
        render_opportunities_tab()

    with tabs[2]:
        render_thesis_tab(tickers)

    with tabs[3]:
        render_risk_tab(tickers)

    with tabs[4]:
        render_governance_tab(rows)


main()