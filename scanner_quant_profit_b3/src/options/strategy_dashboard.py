"""
Radar Quant — Interface Profissional de Trading de Opções B3
Dark mode · Cards · Nível XP / BTG / TradingView
"""
from __future__ import annotations

import streamlit.components.v1 as components
import html
import math
import sqlite3
import sys
from datetime import datetime, time as dtime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── CSS dark mode completo ───────────────────────────────────────────────────

_CSS = """
<style>
/* === BASE === */
section.main > div { padding-top: 0.5rem; }

/* === COMPONENTES CUSTOM === */

/* HEADER */
.rq-header {
    background: linear-gradient(135deg, #060B14 0%, #0D1F38 55%, #060B14 100%);
    border: 1px solid #1E3A5F;
    border-radius: 12px;
    padding: 18px 26px 16px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
}
.rq-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #1D4ED8 0%, #7C3AED 50%, #0EA5E9 100%);
}
.rq-header-top {
    display: flex; justify-content: space-between;
    align-items: center; flex-wrap: wrap; gap: 12px;
}
.rq-title {
    font-size: 1.5rem; font-weight: 900; color: #F1F5F9;
    letter-spacing: -0.5px; margin: 0;
}
.rq-title em { color: #3B82F6; font-style: normal; }
.rq-meta  { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.rq-clock {
    font-size: 1.35rem; font-weight: 700; color: #64748B;
    font-variant-numeric: tabular-nums; font-family: monospace;
}
.rq-market {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 800; letter-spacing: 0.5px;
}
.mkt-open  { background: #052e16; color: #22C55E; border: 1px solid #166534; }
.mkt-close { background: #1c0a0a; color: #EF4444; border: 1px solid #7f1d1d; }
.rq-pill {
    display: inline-flex; align-items: center; gap: 5px;
    background: #0D1F38; border: 1px solid #1E3A5F;
    padding: 3px 11px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; color: #60A5FA;
}
.rq-sub { font-size: 0.75rem; color: #334155; margin-top: 5px; }

/* KPI STRIP */
.kpi-strip { display: flex; gap: 10px; margin-bottom: 20px; }
.kpi-card {
    flex: 1; background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; padding: 14px 16px; text-align: center;
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.kc-green::before  { background: #22C55E; }
.kc-amber::before  { background: #F59E0B; }
.kc-blue::before   { background: #3B82F6; }
.kc-purple::before { background: #7C3AED; }
.kc-slate::before  { background: #475569; }
.kpi-label { font-size: 0.63rem; color: #334155; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { font-size: 1.6rem; font-weight: 900; color: #F1F5F9; line-height: 1.1; }
.kpi-sub   { font-size: 0.65rem; color: #1E3A5F; margin-top: 2px; color: #475569; }

/* SECTION TITLE */
.sec-title {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; color: #334155;
    margin: 22px 0 12px;
    display: flex; align-items: center; gap: 8px;
}
.sec-title::after { content: ''; flex: 1; height: 1px; background: #1E2D42; }

/* TOP TRADE CARD */
.tt-card {
    background: #111827; border: 1px solid #1E2D42; border-radius: 12px;
    padding: 16px; height: 100%; box-sizing: border-box;
    transition: border-color 0.2s;
}
.tt-card:hover { border-color: #2D4A6B; }
.tt-card-forte  { border-left: 4px solid #22C55E !important; }
.tt-card-obs    { border-left: 4px solid #F59E0B !important; }
.tt-card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.tt-ativo { font-size: 1.35rem; font-weight: 900; color: #F1F5F9; }
.tt-opcao { font-size: 0.74rem; color: #334155; margin-top: 2px; font-family: monospace; }
.tt-score-val { font-size: 1.9rem; font-weight: 900; line-height: 1; }
.tt-score-lbl { font-size: 0.58rem; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; }
.tt-badges { margin-bottom: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.tt-divider { border-top: 1px solid #1E2D42; margin: 10px 0; }
.tt-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.tt-key { font-size: 0.68rem; color: #334155; }
.tt-val { font-size: 0.8rem; font-weight: 700; color: #E2E8F0; }
.tt-val-g { color: #22C55E !important; }
.tt-val-r { color: #EF4444 !important; }
.tt-val-a { color: #F59E0B !important; }
.tt-bar-bg { background: #1E2D42; border-radius: 3px; height: 3px; margin-top: 10px; }
.tt-bar    { height: 3px; border-radius: 3px; }

/* SETUP CARD (lista completa) */
.sc {
    background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; margin-bottom: 12px; overflow: hidden;
}
.sc-op   { border-left: 4px solid #22C55E; }
.sc-est  { border-left: 4px solid #F59E0B; }
.sc-desc { border-left: 4px solid #EF4444; }
.sc-head { padding: 14px 18px 10px; border-bottom: 1px solid #162034; }
.sc-body { padding: 14px 18px; }
.sc-foot {
    background: #0A0E1A; padding: 7px 18px;
    font-size: 0.72rem; color: #1E3A5F; font-family: monospace;
    border-top: 1px solid #162034; color: #334155;
}
.sc-title-row { display: flex; justify-content: space-between; align-items: flex-start; }
.sc-ativo { font-size: 1.15rem; font-weight: 800; color: #F1F5F9; }
.sc-nome  { font-size: 0.82rem; color: #334155; }
.sc-score-block { text-align: right; }
.sc-score-val { font-size: 1.1rem; font-weight: 900; }
.sc-meta { margin-top: 8px; display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }
.sc-prog { background: #1E2D42; border-radius: 3px; height: 3px; margin-top: 10px; }

.sc-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.sc-col-head {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.8px; color: #334155; margin-bottom: 7px;
}
.sc-row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 0.78rem; }
.sc-dk { color: #334155; }
.sc-dv { font-weight: 700; color: #CBD5E1; }
.sc-dv-g { color: #22C55E !important; }
.sc-dv-r { color: #EF4444 !important; }

.sc-scenarios { display: flex; gap: 10px; padding: 0 18px 14px; }
.sc-win  { background: #052e16; border-left: 3px solid #22C55E; padding: 8px 12px; border-radius: 0 6px 6px 0; flex: 1; font-size: 0.76rem; color: #4ADE80; }
.sc-lose { background: #1c0909; border-left: 3px solid #EF4444; padding: 8px 12px; border-radius: 0 6px 6px 0; flex: 1; font-size: 0.76rem; color: #FCA5A5; }

.human-text { font-size: 0.84rem; color: #64748B; line-height: 1.65; }
.slabel {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.8px; color: #334155; margin-bottom: 6px; display: block;
}

/* BADGES */
.badge {
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 0.67rem; font-weight: 800; letter-spacing: 0.3px;
}
.b-op    { background: #052e16; color: #22C55E; }
.b-est   { background: #1c1100; color: #F59E0B; }
.b-desc  { background: #1c0909; color: #EF4444; }
.b-forte { background: #052e16; color: #22C55E; border: 1px solid #166534; }
.b-obs   { background: #1c1100; color: #F59E0B; border: 1px solid #92400e; }
.b-alta  { background: #0c1f40; color: #60A5FA; }
.b-baixa { background: #1c0a1c; color: #F472B6; }
.b-lat   { background: #1A1A2E; color: #64748B; }
.b-vol   { background: #16023e; color: #C4B5FD; }
.b-renda { background: #052e16; color: #34D399; }
.b-prot  { background: #1c0e00; color: #FCD34D; }
.b-margin { background: #1c0909; color: #FCA5A5; }

/* DETAIL PANEL */
.detail-box {
    background: #0D1421; border: 1px solid #1E3A5F;
    border-radius: 12px; padding: 22px; margin-top: 16px;
}
.detail-box h4 { color: #94A3B8; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 8px; }
.detail-box p  { color: #64748B; font-size: 0.84rem; line-height: 1.65; margin: 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 14px; }
.detail-block {
    background: #111827; border: 1px solid #1E2D42;
    border-radius: 8px; padding: 14px;
}

/* DECISION FLOW — top trades highlight */
.decision-q {
    display: flex; align-items: baseline; gap: 8px;
    padding: 4px 0; border-bottom: 1px dashed #1E2D42;
    margin-bottom: 3px;
}
.decision-q:last-child { border-bottom: none; }
.dq-num  { font-size: 0.6rem; color: #1E3A5F; min-width: 14px; font-weight: 700; }
.dq-key  { font-size: 0.67rem; color: #334155; min-width: 80px; }
.dq-val  { font-size: 0.82rem; font-weight: 800; color: #E2E8F0; }

/* MONEY badge — additional */
.b-atm  { background: #1A1A2E; color: #94A3B8; border: 1px solid #1E2D42; }
.b-itm  { background: #0c1f40; color: #60A5FA; border: 1px solid #1E3A5F; }
.b-otm  { background: #16023e; color: #A78BFA; border: 1px solid #2e1065; }

/* SIDEBAR clean */
.css-1d391kg, [data-testid="stSidebar"] {
    background: #060B14 !important;
    border-right: 1px solid #0D1F38;
}

/* TABS */
[data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #1E2D42; }
[data-baseweb="tab"]      { color: #334155 !important; font-size: 0.78rem !important; }
[aria-selected="true"]    { color: #60A5FA !important; border-bottom: 2px solid #3B82F6 !important; }

/* METRIC dark */
[data-testid="stMetric"] { background: #111827; border: 1px solid #1E2D42; border-radius: 8px; padding: 10px 14px; }
[data-testid="stMetricLabel"] p { color: #334155 !important; font-size: 0.68rem !important; text-transform: uppercase; letter-spacing: 0.8px; }
[data-testid="stMetricValue"] { color: #F1F5F9 !important; }

/* SCROLLBAR */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D42; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2D4A6B; }

/* ── HERO TOP TRADE ── */
.hero-card {
    background: linear-gradient(135deg, #060B14 0%, #0D1F38 65%, #060B14 100%);
    border: 1px solid #1E3A5F; border-left: 6px solid #22C55E;
    border-radius: 16px; padding: 28px 32px; margin-bottom: 20px;
    position: relative; overflow: hidden;
}
.hero-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #22C55E 0%, #3B82F6 55%, #22C55E 100%);
}
.hero-rank { font-size: 0.62rem; font-weight: 900; color: #334155; text-transform: uppercase; letter-spacing: 2px; }
.hero-ativo { font-size: 2.6rem; font-weight: 900; color: #F1F5F9; letter-spacing: -1px; line-height: 1.1; margin: 6px 0 2px; }
.hero-opcao { font-family: monospace; font-size: 1rem; color: #475569; }
.hero-score { font-size: 3.8rem; font-weight: 900; line-height: 1; }
.hero-score-lbl { font-size: 0.6rem; color: #334155; text-transform: uppercase; letter-spacing: 1px; }
.hero-narrative {
    font-size: 0.88rem; color: #64748B; line-height: 1.75; margin: 16px 0 14px;
    border-left: 3px solid #1E3A5F; padding: 10px 14px;
    background: rgba(9,13,24,0.6); border-radius: 0 6px 6px 0;
}
.hero-actions { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.hero-action { border-radius: 10px; padding: 14px 12px; text-align: center; }
.hero-action-lbl { font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: block; }
.hero-action-val { font-size: 1.2rem; font-weight: 900; display: block; }
.hero-action-sub { font-size: 0.66rem; margin-top: 3px; display: block; opacity: 0.7; }
.hero-stats { display: flex; gap: 22px; flex-wrap: wrap; border-top: 1px solid #1E2D42; padding-top: 12px; margin-top: 6px; }
.hero-stat-k { font-size: 0.6rem; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; }
.hero-stat-v { font-size: 0.92rem; font-weight: 800; color: #94A3B8; }

/* ── SETUP CARD — action strip ── */
.sc-actions { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 10px; }
.sc-action { border-radius: 7px; padding: 7px 8px; text-align: center; }
.sc-action-lbl { font-size: 0.54rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; display: block; }
.sc-action-val { font-size: 0.84rem; font-weight: 900; display: block; }

/* ── DECISION STRIP (hero) ── */
.decision-strip {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
    background: rgba(2,6,23,0.7); border: 1px solid #1E3A5F;
    border-radius: 10px; padding: 14px 16px; margin: 14px 0;
}
.ds-item { display: flex; flex-direction: column; gap: 3px; }
.ds-q { font-size: 0.58rem; color: #334155; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700; }
.ds-a { font-size: 0.92rem; font-weight: 900; color: #E2E8F0; }
.ds-a-yes { color: #22C55E !important; }
.ds-a-no  { color: #EF4444 !important; }

/* ── COMPACT CARD (grid 3-col) ── */
.cc {
    background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; padding: 14px 14px 10px;
    box-sizing: border-box; transition: border-color 0.15s, transform 0.1s;
    margin-bottom: 0;
}
.cc:hover { border-color: #2D4A6B; transform: translateY(-1px); }
.cc-top { display: flex; justify-content: space-between; align-items: flex-start; }
.cc-ativo { font-size: 1.25rem; font-weight: 900; color: #F1F5F9; line-height: 1.1; }
.cc-opcao { font-size: 0.68rem; color: #334155; font-family: monospace; margin-top: 2px; }
.cc-score { font-size: 1.7rem; font-weight: 900; line-height: 1; }
.cc-score-lbl { font-size: 0.52rem; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; text-align: right; }
.cc-badges { display: flex; gap: 5px; flex-wrap: wrap; margin: 7px 0 8px; align-items: center; }
.cc-dte { font-size: 0.62rem; color: #475569; }
.cc-grid4 { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-bottom: 8px; }
.cc-kv { background: #0A0E1A; border-radius: 5px; padding: 5px 8px; }
.cc-k { font-size: 0.55rem; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 1px; }
.cc-v { font-size: 0.88rem; font-weight: 800; }
.cc-ações { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; }
.cc-e { background: #0A0E1A; border: 1px solid #1E2D42; border-radius: 5px; padding: 5px 4px; text-align: center; }
.cc-s { background: #1c0909; border: 1px solid #7f1d1d; border-radius: 5px; padding: 5px 4px; text-align: center; }
.cc-t { background: #052e16; border: 1px solid #166534; border-radius: 5px; padding: 5px 4px; text-align: center; }
.cc-albl { font-size: 0.52rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; display: block; margin-bottom: 2px; }
.cc-aval { font-size: 0.76rem; font-weight: 900; display: block; }
.cc-bar { background: #1E2D42; border-radius: 2px; height: 2px; margin-top: 9px; }
</style>
"""

_CLOCK_JS = """<script>
(function(){function t(){var e=document.getElementById('rq-clock-val');if(e){var n=new Date();e.textContent=n.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}setTimeout(t,1000);}t();})();
</script>"""

# ── Helpers de mapeamento ────────────────────────────────────────────────────

_STATUS_CLS   = {"OPERACIONAL": "op",   "ESTUDO": "est",  "DESCARTAR": "desc"}
_STATUS_ICON  = {"OPERACIONAL": "✅",   "ESTUDO": "📋",   "DESCARTAR": "❌"}
_STATUS_BADGE = {"OPERACIONAL": "b-op", "ESTUDO": "b-est", "DESCARTAR": "b-desc"}

_DIR_MAP = {
    "SPREAD_ALTA":  ("📈 ALTA",         "b-alta"),
    "SPREAD_BAIXA": ("📉 BAIXA",        "b-baixa"),
    "CONDOR":       ("⬌ LATERAL",      "b-lat"),
    "BUTTERFLY":    ("⬌ LATERAL",      "b-lat"),
    "VOLATILIDADE": ("⚡ VOLATILIDADE", "b-vol"),
    "RENDA":        ("💰 RENDA",        "b-renda"),
    "PROTECAO":     ("🛡 PROTEÇÃO",     "b-prot"),
    "DIRECIONAL":   ("📈 DIRECIONAL",   "b-alta"),
}

_CAT_STYLE = {
    "BAIXO":                      ("#052e16", "#22C55E"),
    "MODERADO":                   ("#1c1100", "#F59E0B"),
    "ALTO":                       ("#1c0e00", "#F97316"),
    "ALTO_RISCO_NAO_RECOMENDADO": ("#1c0909", "#EF4444"),
}

_CAT_DESC = {
    "BAIXO":                      "Baixo risco — perfil conservador",
    "MODERADO":                   "Risco moderado — gestão ativa",
    "ALTO":                       "⚠️ Risco alto — stop obrigatório",
    "ALTO_RISCO_NAO_RECOMENDADO": "🚫 Não recomendado",
}


def _market_status():
    brt = timezone(timedelta(hours=-3))
    now = datetime.now(brt)
    t   = now.time()
    is_open = (
        now.weekday() < 5 and
        dtime(10, 0) <= t <= dtime(17, 55)
    )
    return is_open, now.strftime("%H:%M:%S"), now.strftime("%d/%m/%Y %a")


def _score_color(score: float) -> str:
    if score >= 70:
        return "#22C55E"
    if score >= 50:
        return "#F59E0B"
    return "#EF4444"


def _compact_card(opp) -> str:
    """Card compacto para grid 3 colunas — decisão em 5 segundos."""
    p          = opp.payoff
    sc_color   = _score_color(opp.score)
    sc_w       = min(int(opp.score), 100)
    dir_text, dir_cls = _DIR_MAP.get(p.strategy_type, ("NEUTRO", "b-lat"))
    status_badge = _STATUS_BADGE.get(opp.status, "b-est")
    status_icon  = _STATUS_ICON.get(opp.status, "")
    sl_color     = {"OPERACIONAL": "#22C55E", "ESTUDO": "#F59E0B"}.get(opp.status, "#EF4444")

    profit_txt = f"R${p.max_profit:,.0f}" if not math.isinf(p.max_profit) else "∞"
    loss_txt   = f"R${p.max_loss:,.0f}"   if not math.isinf(p.max_loss)   else "∞"
    rr_txt     = f"{p.risk_reward:.1f}x"  if not math.isinf(p.risk_reward) else "∞"

    main_leg  = next((l for l in p.legs if l.option_type != "STOCK"), None)
    opcao_str = main_leg.ticker if main_leg else p.name
    entry_val = f"R${main_leg.price:.4f}" if main_leg else "—"
    stop_pct  = "−30%"
    alvo_pct  = "+50%"

    return f"""
<div class="cc" style="border-left:4px solid {sl_color}">
    <div class="cc-top">
        <div>
        <div class="cc-ativo">{p.underlying}</div>
        <div class="cc-opcao">{opcao_str}</div>
        </div>
        <div>
        <div class="cc-score" style="color:{sc_color}">{opp.score:.0f}</div>
        <div class="cc-score-lbl">score</div>
        </div>
    </div>

    <div class="cc-badges">
        <span class="badge {status_badge}">{status_icon} {opp.status}</span>
        <span class="badge {dir_cls}">{dir_text}</span>
        <span class="cc-dte">DTE {p.dte}d · {p.expiry}</span>
    </div>

    <div class="cc-grid4">
        <div class="cc-kv"><span class="cc-k">P(Lucro)</span><span class="cc-v" style="color:#22C55E">{opp.prob_profit:.0%}</span></div>
        <div class="cc-kv"><span class="cc-k">R / R</span><span class="cc-v" style="color:#3B82F6">{rr_txt}</span></div>
        <div class="cc-kv"><span class="cc-k">Ganho Máx</span><span class="cc-v" style="color:#22C55E">{profit_txt}</span></div>
        <div class="cc-kv"><span class="cc-k">Risco Máx</span><span class="cc-v" style="color:#EF4444">{loss_txt}</span></div>
    </div>

    <div class="cc-ações">
        <div class="cc-e">
        <span class="cc-albl" style="color:#475569">Entrada</span>
        <span class="cc-aval" style="color:#3B82F6">{entry_val}</span>
        </div>
        <div class="cc-s">
        <span class="cc-albl" style="color:#ef4444">Stop</span>
        <span class="cc-aval" style="color:#EF4444">{stop_pct}</span>
        </div>
        <div class="cc-t">
        <span class="cc-albl" style="color:#22c55e">Alvo</span>
        <span class="cc-aval" style="color:#22C55E">{alvo_pct}</span>
        </div>
    </div>

    <div class="cc-bar"><div style="width:{sc_w}%;height:2px;border-radius:2px;background:{sc_color}"></div></div>
    </div>"""


def _moneyness(spot: float, strike: float, opt_type: str = "CALL") -> str:
    diff = (spot - strike) / spot if spot else 0
    if abs(diff) < 0.02:
        return ("ATM", "b-lat")
    if opt_type.upper() == "CALL":
        return ("ITM", "b-alta") if diff > 0 else ("OTM", "b-vol")
    # PUT
    return ("ITM", "b-baixa") if diff < 0 else ("OTM", "b-vol")


def _forte_badge(opp) -> str:
    if opp.score >= 70 and opp.prob_profit >= 0.60:
        return '<span class="badge b-forte">🔥 FORTE</span>'
    if opp.status == "OPERACIONAL":
        return '<span class="badge b-op">✅ OPERACIONAL</span>'
    return '<span class="badge b-obs">⚠️ OBSERVAR</span>'


# ── Relatório humanizado ─────────────────────────────────────────────────────

def generate_human_report(opp) -> dict:
    p   = opp.payoff
    cnd = opp.market_condition.value

    _ctx = {
        "ALTA_FORTE":
            f"{p.underlying} em tendência de alta forte, acima das médias de curto e médio prazo. "
            f"Momentum comprador dominante com RSI acima de 58.",
        "ALTA_MODERADA":
            f"{p.underlying} apresenta viés comprador moderado, acima da MM21. "
            f"Setup maduro para estruturas direcionais sem excesso de euforia.",
        "BAIXA_FORTE":
            f"{p.underlying} em queda acentuada, abaixo de todas as referências técnicas. "
            f"Pressão vendedora com RSI abaixo de 42. Atenção redobrada.",
        "BAIXA_MODERADA":
            f"{p.underlying} com viés negativo moderado, abaixo da MM21. "
            f"Fluxo direcional para baixo sem reversão visível.",
        "LATERAL":
            f"{p.underlying} em consolidação lateral dentro de range definido. "
            f"Mercado ideal para estratégias de venda de prêmio.",
        "ALTA_VOL":
            f"{p.underlying} com volatilidade histórica elevada acima da média. "
            f"Movimentos bruscos em qualquer direção são prováveis.",
        "BAIXA_VOL":
            f"{p.underlying} com volatilidade comprimida abaixo da média histórica. "
            f"Mercado em silêncio — ideal para vender prêmio.",
        "INDEFINIDO":
            f"{p.underlying} sem tendência definida. Sinal técnico inconclusivo.",
    }
    contexto = _ctx.get(cnd, f"{p.underlying} em análise técnica.")

    prob_desc = (
        f"probabilidade de lucro elevada ({opp.prob_profit:.0%})"   if opp.prob_profit >= 0.65 else
        f"probabilidade de lucro aceitável ({opp.prob_profit:.0%})" if opp.prob_profit >= 0.50 else
        f"probabilidade abaixo de 50% ({opp.prob_profit:.0%}) — setup especulativo"
    )
    adh_desc = (
        "alta aderência ao cenário" if opp.scenario_adherence >= 0.85 else
        "aderência moderada"        if opp.scenario_adherence >= 0.65 else
        "aderência baixa — cautela"
    )
    leitura = (
        f"{adh_desc.capitalize()} e {prob_desc}. "
        f"Volatilidade histórica de {opp.hv:.1%} usada nos cálculos."
    )

    _est = {
        "SPREAD_ALTA":
            "Trava de alta — captura movimento ascendente com custo e risco definidos. "
            "Ideal para alta moderada até a resistência identificada.",
        "SPREAD_BAIXA":
            "Trava de baixa — posicionamento para queda controlada com risco limitado ao débito pago.",
        "CONDOR":
            "Iron Condor — recebe crédito e lucra se o ativo ficar dentro do range até o vencimento.",
        "BUTTERFLY":
            "Butterfly — aposta no pin: lucra ao máximo se o ativo fechar no strike central.",
        "VOLATILIDADE":
            "Estratégia de volatilidade — lucra com grande movimento em qualquer direção.",
        "RENDA":
            "Geração de renda — vende prêmio e lucra com a passagem do tempo.",
        "PROTECAO":
            "Proteção de carteira — funciona como seguro contra quedas abruptas.",
        "DIRECIONAL":
            "Compra direcional pura — alavanca o movimento do ativo com risco limitado ao prêmio pago.",
    }
    estrategia = _est.get(p.strategy_type, p.market_view)

    legs_list = [
        f"{'Compra' if l.direction == 'BUY' else 'Venda'} {l.ticker} "
        f"(K={l.strike:.2f}, vto {l.expiry})"
        for l in p.legs if l.option_type != "STOCK"
    ]
    por_que = "; ".join(legs_list) + ". " if legs_list else ""
    _cat_desc = {
        "BAIXO":                      "Estrutura de baixo risco adequada para perfis conservadores.",
        "MODERADO":                   "Risco moderado e controlado, boa relação capital/retorno.",
        "ALTO":                       "Risco elevado. Exige gestão ativa e stop claro.",
        "ALTO_RISCO_NAO_RECOMENDADO": "ATENÇÃO: risco muito alto. Apenas com experiência e gestão rigorosa.",
    }
    por_que += _cat_desc.get(p.risk_category, "")

    risco = (
        f"Risco ilimitado — sem teto de perda. {p.risk_observation}"
        if math.isinf(p.max_loss)
        else f"Perda máxima de R${p.max_loss:,.0f} por lote. {p.risk_observation}"
    )

    return {
        "contexto":   html.escape(str(contexto)),
        "leitura":    html.escape(str(leitura)),
        "estrategia": html.escape(str(estrategia)),
        "por_que":    html.escape(str(por_que)),
        "cenario":    html.escape(str(p.best_scenario)),
        "risco":      html.escape(str(risco)),
}


def generate_human_text(row: dict) -> str:
    """
    Gera texto humanizado a partir de um dict/row de DataFrame.

    Chaves esperadas: underlying, opcao, prob_profit, hv, market_condition,
    strategy_type, risk_category, max_loss, max_profit, best_scenario,
    risk_observation (opcionais — função é tolerante a ausências).

    Retorna HTML com as seções: Ativo · Leitura · Estratégia ·
    Por que essa opção · Cenário esperado · Risco.
    """
    ativo    = row.get("underlying", "Ativo")
    opcao    = row.get("opcao", row.get("strategy", ""))
    prob     = float(row.get("prob_profit", 0))
    hv       = float(row.get("hv", 0))
    cnd      = str(row.get("market_condition", "INDEFINIDO")).upper().replace("-", "_")
    stype    = str(row.get("strategy_type", row.get("strategy", "DIRECIONAL"))).upper()
    rcat     = str(row.get("risk_category", "MODERADO")).upper()
    max_loss = row.get("max_loss", None)
    max_prof = row.get("max_profit", None)
    best_sc  = row.get("best_scenario", "")
    risk_obs = row.get("risk_observation", "")

    _ctx_map = {
        "ALTA_FORTE":    f"{ativo} apresenta forte momentum de alta, acima das médias de curto e médio prazo com RSI saudável.",
        "ALTA_MODERADA": f"{ativo} mostra viés comprador moderado. Setup maduro sem excesso de euforia.",
        "BAIXA_FORTE":   f"{ativo} em queda consistente, abaixo de todas as referências técnicas.",
        "BAIXA_MODERADA":f"{ativo} com viés negativo moderado. Fluxo direcional para baixo.",
        "LATERAL":       f"{ativo} em consolidação. Range definido, ideal para venda de prêmio.",
        "ALTA_VOL":      f"{ativo} com volatilidade elevada. Movimentos bruscos são prováveis.",
        "BAIXA_VOL":     f"{ativo} em silêncio — volatilidade comprimida abaixo da média histórica.",
        "INDEFINIDO":    f"{ativo} sem tendência definida no momento.",
    }
    leitura_ativo = _ctx_map.get(cnd, f"{ativo} em análise.")

    if prob >= 0.65:
        leitura_prob = f"Alta probabilidade de lucro ({prob:.0%}) favorece a entrada."
    elif prob >= 0.50:
        leitura_prob = f"Probabilidade de lucro aceitável ({prob:.0%}). Gestão de risco é essencial."
    else:
        leitura_prob = f"Setup especulativo — probabilidade abaixo de 50% ({prob:.0%}). Tamanho de posição reduzido."

    _est_map = {
        "SPREAD_ALTA":  "Trava de alta captura movimento ascendente com custo e risco definidos.",
        "SPREAD_BAIXA": "Trava de baixa para queda controlada. Risco limitado ao débito pago.",
        "CONDOR":       "Iron Condor recebe crédito e lucra se o ativo ficar dentro do range.",
        "BUTTERFLY":    "Butterfly aposta no pin no strike central no vencimento.",
        "VOLATILIDADE": "Estratégia de volatilidade lucra com grande movimento em qualquer direção.",
        "RENDA":        "Geração de renda via venda de prêmio. Theta a favor.",
        "PROTECAO":     "Proteção de carteira — funciona como seguro contra quedas abruptas.",
        "DIRECIONAL":   "Compra direcional com risco limitado ao prêmio pago.",
    }
    est_text = _est_map.get(stype, "Estrutura aderente ao cenário identificado.")

    if opcao:
        por_que = f"A opção {opcao} apresenta boa relação com o cenário atual e favorece a estratégia escolhida."
    else:
        por_que = "Estrutura montada com as opções de melhor liquidez e aderência ao cenário."

    if rcat in ("ALTO", "ALTO_RISCO_NAO_RECOMENDADO"):
        por_que += " Atenção: risco elevado — use stops e posição reduzida."

    cenario = best_sc or f"Lucro máximo se {ativo} seguir o movimento esperado até o vencimento."

    if max_loss is None or (isinstance(max_loss, float) and math.isinf(max_loss)):
        risco_text = f"Risco ilimitado. {risk_obs}".strip()
    else:
        try:
            risco_text = f"Perda máxima de R${float(max_loss):,.0f} por lote. {risk_obs}".strip()
        except (ValueError, TypeError):
            risco_text = str(max_loss)

    sections = [
        ("Ativo",              leitura_ativo),
        ("Leitura",            leitura_prob),
        ("Estratégia",         est_text),
        ("Por que essa opção", por_que),
        ("Cenário esperado",   cenario),
        ("Risco",              risco_text),
    ]
    parts = []
    for label, content in sections:
        if content:
            parts.append(
                f'<span class="slabel">{label}</span>'
                f'<span class="human-text">{content}</span>'
            )
    return "".join(f'<div style="margin-bottom:10px">{p}</div>' for p in parts)


# ── TOP TRADE CARD (horizontal strip) ───────────────────────────────────────

def _top_trade_card(opp, rank: int) -> str:
    p = opp.payoff

    dir_text, dir_cls = _DIR_MAP.get(p.strategy_type, ("NEUTRO", "b-lat"))
    sc = opp.score
    sc_color = _score_color(sc)
    sc_w     = min(int(sc), 100)

    if opp.score >= 70 and opp.prob_profit >= 0.60:
        forte_html = '<span class="badge b-forte">🔥 FORTE</span>'
        card_cls   = "tt-card-forte"
    else:
        forte_html = '<span class="badge b-obs">⚠️ OBSERVAR</span>'
        card_cls   = "tt-card-obs"

    loss_txt   = f"R${p.max_loss:,.0f}"   if not math.isinf(p.max_loss)   else "Ilimitado"
    profit_txt = f"R${p.max_profit:,.0f}" if not math.isinf(p.max_profit) else "Ilimitado"
    loss_cls   = "tt-val-r" if not math.isinf(p.max_loss) else "tt-val-r"
    profit_cls = "tt-val-g"

    main_leg   = next((l for l in p.legs if l.option_type != "STOCK"), None)
    opcao_str  = main_leg.ticker if main_leg else p.name

    rr_txt = f"{p.risk_reward:.1f}x" if not math.isinf(p.risk_reward) else "∞"

    # moneyness badge
    if main_leg and p.stock_price:
        money_label, money_cls = _moneyness(p.stock_price, main_leg.strike, main_leg.option_type)
        money_html = f'<span class="badge {money_cls}">{money_label}</span>'
    else:
        money_html = ""

    # entry / stop / target grid
    if main_leg:
        entry_px = main_leg.price
        stop_val = entry_px * 0.70
        t1_val   = entry_px * 1.50
        action_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:10px">
        <div style="text-align:center;padding:8px 4px;background:#0A0E1A;border-radius:7px;border:1px solid #1E2D42">
        <div style="font-size:0.54rem;color:#475569;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px">👉 Entrada</div>
        <div style="font-size:0.85rem;font-weight:900;color:#3B82F6">R${entry_px:.4f}</div>
        </div>
        <div style="text-align:center;padding:8px 4px;background:#1c0909;border-radius:7px;border:1px solid #7f1d1d">
        <div style="font-size:0.54rem;color:#ef4444;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px">⛔ Stop</div>
        <div style="font-size:0.85rem;font-weight:900;color:#EF4444">−30%</div>
        </div>
        <div style="text-align:center;padding:8px 4px;background:#052e16;border-radius:7px;border:1px solid #166534">
        <div style="font-size:0.54rem;color:#22c55e;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px">🎯 Alvo</div>
        <div style="font-size:0.85rem;font-weight:900;color:#22C55E">+50%</div>
        </div>
    </div>"""
    else:
        action_html = f"""
    <div style="display:flex;justify-content:space-between;padding:8px 0;font-size:0.78rem">
        <span style="color:#334155">Risco <strong style="color:#EF4444">{loss_txt}</strong></span>
        <span style="color:#334155">Alvo <strong style="color:#22C55E">{profit_txt}</strong></span>
    </div>"""

    return f"""
    <div class="tt-card {card_cls}">
    <div class="tt-card-top">
        <div>
        <div class="tt-ativo">#{rank} {p.underlying}</div>
        <div class="tt-opcao">{opcao_str}</div>
        </div>
        <div style="text-align:right">
        <div class="tt-score-val" style="color:{sc_color}">{sc:.0f}</div>
        <div class="tt-score-lbl">score</div>
        </div>
    </div>

    <div class="tt-badges">
        {forte_html}
        <span class="badge {dir_cls}">{dir_text}</span>
        {money_html}
    </div>

    <div class="tt-divider"></div>

    {action_html}

    <div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-top:4px">
        <span style="color:#334155">P(lucro) <strong style="color:#94A3B8">{opp.prob_profit:.0%}</strong></span>
        <span style="color:#334155">R/R <strong style="color:#94A3B8">{rr_txt}</strong></span>
        <span style="color:#334155">DTE <strong style="color:#94A3B8">{p.dte}d</strong></span>
    </div>

    <div class="tt-bar-bg">
        <div class="tt-bar" style="width:{sc_w}%;background:{sc_color}"></div>
    </div>
    </div>
    """


# ── HERO CARD — Top Trade #1 (destaque total) ───────────────────────────────

def _top_trade_hero(opp) -> str:
    p        = opp.payoff
    sc       = opp.score
    sc_color = _score_color(sc)
    sc_w     = min(int(sc), 100)

    dir_text, dir_cls = _DIR_MAP.get(p.strategy_type, ("NEUTRO", "b-lat"))

    main_leg  = next((l for l in p.legs if l.option_type != "STOCK"), None)
    opcao_str = main_leg.ticker if main_leg else p.name

    report    = generate_human_report(opp)
    narrative = f"{report['contexto']} {report['leitura']}"

    rr_txt    = f"{p.risk_reward:.1f}x" if not math.isinf(p.risk_reward) else "∞"

    if main_leg:
        entry_px   = main_leg.price
        stop_px    = entry_px * 0.70
        t1_px      = entry_px * 1.50
        entry_cond = (p.entry_condition or "Condição técnica favorável")[:60]
        actions_html = f"""
    <div class="hero-actions">
    <div class="hero-action" style="background:#0D1421;border:1px solid #1E3A5F">
        <span class="hero-action-lbl" style="color:#475569">👉 Entrada</span>
        <span class="hero-action-val" style="color:#3B82F6">R${entry_px:.4f}</span>
        <span class="hero-action-sub" style="color:#334155">{entry_cond}</span>
    </div>
    <div class="hero-action" style="background:#1c0909;border:1px solid #7f1d1d">
        <span class="hero-action-lbl" style="color:#ef4444">⛔ Stop</span>
        <span class="hero-action-val" style="color:#EF4444">R${stop_px:.4f}</span>
        <span class="hero-action-sub" style="color:#7f1d1d">−30% do prêmio</span>
    </div>
    <div class="hero-action" style="background:#052e16;border:1px solid #166534">
        <span class="hero-action-lbl" style="color:#22c55e">🎯 Alvo</span>
        <span class="hero-action-val" style="color:#22C55E">R${t1_px:.4f}</span>
        <span class="hero-action-sub" style="color:#166534">+50% do prêmio</span>
    </div>
    </div>"""
    else:
        loss_txt   = f"R${p.max_loss:,.0f}"   if not math.isinf(p.max_loss)   else "Ilimitado"
        profit_txt = f"R${p.max_profit:,.0f}" if not math.isinf(p.max_profit) else "Ilimitado"
        actions_html = f"""
    <div class="hero-actions">
    <div class="hero-action" style="background:#0D1421;border:1px solid #1E3A5F">
        <span class="hero-action-lbl" style="color:#475569">👉 Estratégia</span>
        <span class="hero-action-val" style="color:#60A5FA;font-size:1rem">{p.name}</span>
    </div>
    <div class="hero-action" style="background:#1c0909;border:1px solid #7f1d1d">
        <span class="hero-action-lbl" style="color:#ef4444">⛔ Risco máx</span>
        <span class="hero-action-val" style="color:#EF4444">{loss_txt}</span>
    </div>
    <div class="hero-action" style="background:#052e16;border:1px solid #166534">
        <span class="hero-action-lbl" style="color:#22c55e">🎯 Ganho máx</span>
        <span class="hero-action-val" style="color:#22C55E">{profit_txt}</span>
    </div>
    </div>"""

    return f"""
    <div class="hero-card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
        <div>
        <div class="hero-rank">🔥 #1 · Top Trade do Dia</div>
        <div class="hero-ativo">{p.underlying}</div>
        <div class="hero-opcao">{opcao_str}</div>
        </div>
        <div style="text-align:right">
        <div class="hero-score" style="color:{sc_color}">{sc:.0f}</div>
        <div class="hero-score-lbl">score</div>
        </div>
    </div>

    <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
        {_forte_badge(opp)}
        <span class="badge {dir_cls}">{dir_text}</span>
        <span style="font-size:0.7rem;color:#334155;align-self:center">DTE {p.dte}d · {p.expiry}</span>
    </div>

    <!-- DECISION STRIP — 6 perguntas respondidas em 1 olhada -->
    <div class="decision-strip">
        <div class="ds-item">
        <span class="ds-q">Vale operar?</span>
        <span class="ds-a ds-a-yes">✅ SIM</span>
        </div>
        <div class="ds-item">
        <span class="ds-q">Qual ativo?</span>
        <span class="ds-a">{p.underlying}</span>
        </div>
        <div class="ds-item">
        <span class="ds-q">Qual opção?</span>
        <span class="ds-a" style="font-family:monospace;font-size:0.82rem">{opcao_str}</span>
        </div>
        <div class="ds-item">
        <span class="ds-q">Qual direção?</span>
        <span class="ds-a">{dir_text}</span>
        </div>
        <div class="ds-item">
        <span class="ds-q">Risco máximo</span>
        <span class="ds-a ds-a-no">{"R${:,.0f}".format(p.max_loss) if not math.isinf(p.max_loss) else "Ilimitado"}</span>
        </div>
        <div class="ds-item">
        <span class="ds-q">Alvo máximo</span>
        <span class="ds-a ds-a-yes">{"R${:,.0f}".format(p.max_profit) if not math.isinf(p.max_profit) else "∞"}</span>
        </div>
    </div>

    <div class="hero-narrative">{narrative}</div>

    {actions_html}

    <div class="hero-stats">
        <div><div class="hero-stat-k">P(Lucro)</div><div class="hero-stat-v" style="color:#22C55E">{opp.prob_profit:.0%}</div></div>
        <div><div class="hero-stat-k">R/R</div><div class="hero-stat-v" style="color:#3B82F6">{rr_txt}</div></div>
        <div><div class="hero-stat-k">Vol Histórica</div><div class="hero-stat-v">{opp.hv:.1%}</div></div>
        <div><div class="hero-stat-k">Aderência</div><div class="hero-stat-v">{opp.scenario_adherence:.0%}</div></div>
        <div><div class="hero-stat-k">Mercado</div><div class="hero-stat-v" style="font-size:0.78rem">{opp.market_condition.value}</div></div>
    </div>

    <div class="tt-bar-bg" style="margin-top:12px">
        <div class="tt-bar" style="width:{sc_w}%;background:{sc_color}"></div>
    </div>
    </div>
    """


# ── SETUP CARD (lista completa) ──────────────────────────────────────────────

def _setup_card(opp) -> str:
    p = opp.payoff
    report = generate_human_report(opp)

    status_cls   = _STATUS_CLS.get(opp.status, "est")
    status_badge = _STATUS_BADGE.get(opp.status, "b-est")
    status_icon  = _STATUS_ICON.get(opp.status, "")
    dir_text, dir_cls = _DIR_MAP.get(p.strategy_type, ("NEUTRO", "b-lat"))

    sc_color = _score_color(opp.score)
    sc_w     = min(int(opp.score), 100)

    cat_bg, cat_fg = _CAT_STYLE.get(p.risk_category, ("#1E2D42", "#94A3B8"))
    cat_short = _CAT_DESC.get(p.risk_category, p.risk_category)

    cost_txt   = f"R${abs(p.net_cost):,.0f} {'déb' if p.net_cost > 0 else 'créd'}"
    profit_txt = f"R${p.max_profit:,.0f}" if not math.isinf(p.max_profit) else "Ilimitado"
    loss_txt   = f"R${p.max_loss:,.0f}"   if not math.isinf(p.max_loss)   else "Ilimitado"
    rr_txt     = f"{p.risk_reward:.1f}x"  if not math.isinf(p.risk_reward) else "∞"
    be_txt     = " · ".join(f"R${b:.2f}" for b in p.breakevens[:2]) or "—"

    margin_html = (
        '<span class="badge b-margin">⚠️ MARGEM</span>'
        if p.requires_margin else ""
    )

    # action strip (entry / stop / alvo)
    _sc_main = next((l for l in p.legs if l.option_type != "STOCK"), None)
    if _sc_main:
        _ep = _sc_main.price
        sc_action_strip = f"""
        <div class="sc-actions" style="margin-top:10px">
        <div class="sc-action" style="background:#0A0E1A;border:1px solid #1E2D42">
            <span class="sc-action-lbl" style="color:#475569">👉 Entrada</span>
            <span class="sc-action-val" style="color:#3B82F6">R${_ep:.4f}</span>
        </div>
        <div class="sc-action" style="background:#1c0909;border:1px solid #7f1d1d">
            <span class="sc-action-lbl" style="color:#ef4444">⛔ Stop</span>
            <span class="sc-action-val" style="color:#EF4444">−30%</span>
        </div>
        <div class="sc-action" style="background:#052e16;border:1px solid #166534">
            <span class="sc-action-lbl" style="color:#22c55e">🎯 Alvo</span>
            <span class="sc-action-val" style="color:#22C55E">+50%</span>
        </div>
        </div>"""
    else:
        sc_action_strip = ""

    # moneyness do leg principal
    if main_leg := next((l for l in p.legs if l.option_type != "STOCK"), None):
        money_label, money_cls = _moneyness(p.stock_price, main_leg.strike, main_leg.option_type)
        money_html = f'<span class="badge {money_cls}">{money_label}</span>'
    else:
        money_html = ""

    legs_footer = "  ·  ".join(
        f"{'C' if l.direction == 'BUY' else 'V'} {l.ticker} "
        f"{l.option_type} K={l.strike:.2f} @ R${l.price:.4f}"
        for l in p.legs if l.option_type != "STOCK"
    ) or f"{p.underlying} @ R${p.stock_price:.2f}"

    return f"""
    <div class="sc sc-{status_cls}">

    <div class="sc-head">
        <div class="sc-title-row">
        <div>
            <span class="sc-ativo">{p.underlying}</span>
            <span class="sc-nome" style="margin-left:8px">{p.name}</span>
            {margin_html}
        </div>
        <div class="sc-score-block">
            <span style="font-size:0.72rem;color:#334155">Score </span>
            <span class="sc-score-val" style="color:{sc_color}">{opp.score:.0f}</span>
        </div>
        </div>
        <div class="sc-meta">
        <span class="badge {status_badge}">{status_icon} {opp.status}</span>
        <span class="badge {dir_cls}">{dir_text}</span>
        {money_html}
        <span style="font-size:0.7rem;font-weight:700;background:{cat_bg};color:{cat_fg};padding:2px 8px;border-radius:10px">{cat_short}</span>
        <span style="font-size:0.72rem;color:#334155">
            DTE {p.dte}d &nbsp;·&nbsp; {p.expiry} &nbsp;·&nbsp;
            {opp.market_condition.value} &nbsp;·&nbsp; Aderência {opp.scenario_adherence:.0%}
        </span>
        </div>
        <div class="sc-prog">
        <div style="width:{sc_w}%;height:3px;border-radius:3px;background:{sc_color}"></div>
        </div>
        {sc_action_strip}
    </div>

    <div class="sc-body" style="border-bottom:1px solid #162034">
        <div class="sc-col-head">📈 Leitura</div>
        <div class="human-text">{report['contexto']} {report['leitura']}</div>
    </div>

    <div class="sc-body">
        <div class="sc-grid">
        <div>
            <div class="sc-col-head">💰 Risco</div>
            <div class="sc-row"><span class="sc-dk">Custo entrada</span><span class="sc-dv">{cost_txt}</span></div>
            <div class="sc-row"><span class="sc-dk">Ganho máx</span><span class="sc-dv sc-dv-g">{profit_txt}</span></div>
            <div class="sc-row"><span class="sc-dk">Perda máx</span><span class="sc-dv sc-dv-r">{loss_txt}</span></div>
            <div class="sc-row"><span class="sc-dk">R/R</span><span class="sc-dv">{rr_txt}</span></div>
            <div class="sc-row"><span class="sc-dk">P(Lucro)</span><span class="sc-dv">{opp.prob_profit:.1%}</span></div>
            <div class="sc-row"><span class="sc-dk">Breakeven</span><span class="sc-dv">{be_txt}</span></div>
        </div>
        <div>
            <div class="sc-col-head">🎯 Estratégia</div>
            <div style="font-size:0.78rem;color:#64748B;line-height:1.5;margin-bottom:10px">{report['estrategia']}</div>
            <div class="sc-col-head" style="margin-top:4px">Por que essa estrutura</div>
            <div style="font-size:0.76rem;color:#475569;line-height:1.45">{report['por_que']}</div>
        </div>
        <div>
            <div class="sc-col-head">⚙️ Entrada / Saída</div>
            <div style="font-size:0.75rem;margin-bottom:8px">
            <div style="color:#334155;font-weight:700;margin-bottom:3px">Entrada</div>
            <div style="color:#64748B">{p.entry_condition}</div>
            </div>
            <div style="font-size:0.75rem">
            <div style="color:#334155;font-weight:700;margin-bottom:3px">Saída</div>
            <div style="color:#64748B">{p.exit_condition}</div>
            </div>
        </div>
        </div>
    </div>

    <div class="sc-scenarios">
        <div class="sc-win"><strong>📈 Quando ganha</strong><br>{p.best_scenario}</div>
        <div class="sc-lose"><strong>📉 Quando perde</strong><br>{p.worst_scenario}</div>
    </div>

    <div class="sc-foot">Pernas: {legs_footer}</div>

    </div>
    """


# ── Detalhe expandido (expander) ─────────────────────────────────────────────

def _detail_html(opp) -> str:
    r = generate_human_report(opp)
    p = opp.payoff
    return f"""
    <div class="detail-box">
    <div class="detail-grid">
        <div class="detail-block">
        <h4>Estratégia</h4>
        <p>{r['estrategia']}</p>
        </div>
        <div class="detail-block">
        <h4>Por que essa estrutura</h4>
        <p>{r['por_que']}</p>
        </div>
        <div class="detail-block">
        <h4>Observação de risco</h4>
        <p style="color:{'#FCA5A5' if p.risk_level == 'ILIMITADO' else '#F59E0B'}">{r['risco']}</p>
        </div>
        <div class="detail-block">
        <h4>Cenário esperado</h4>
        <p>{r['cenario']}</p>
        </div>
    </div>
    </div>
"""


# ── Gráfico de payoff (dark) ─────────────────────────────────────────────────

def _payoff_chart(opp, st_mod, height: int = 380, show_metrics: bool = True):
    """Payoff diagram interativo com Plotly (dark theme TradingView)."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st_mod.warning("Instale plotly: `pip install plotly`")
        return

    p = opp.payoff
    S, pps = p.payoff_array(400)
    Sl = S.tolist()
    Pl = pps.tolist()

    BG, BG2 = "#080D17", "#111827"
    GRID     = "#1E2D42"
    TEXT     = "#64748B"
    BLUE     = "#3B82F6"
    GREEN    = "#22C55E"
    RED      = "#EF4444"
    AMBER    = "#F59E0B"
    WHITE    = "#E2E8F0"

    fig = go.Figure()

    # Zonas coloridas de lucro e perda
    fig.add_trace(go.Scatter(
        x=Sl + Sl[::-1],
        y=[max(0.0, v) for v in Pl] + [0.0] * len(Sl),
        fill="toself", fillcolor="rgba(34,197,94,0.09)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip", showlegend=False, name="Lucro",
    ))
    fig.add_trace(go.Scatter(
        x=Sl + Sl[::-1],
        y=[min(0.0, v) for v in Pl] + [0.0] * len(Sl),
        fill="toself", fillcolor="rgba(239,68,68,0.09)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip", showlegend=False, name="Perda",
    ))

    # Curva principal
    fig.add_trace(go.Scatter(
        x=Sl, y=Pl, mode="lines",
        line=dict(color=BLUE, width=2.8),
        name=p.name,
        hovertemplate="<b>Preço:</b> R$%{x:.2f}<br><b>P&L:</b> R$%{y:.3f}<extra></extra>",
    ))

    # Linha zero
    fig.add_hline(y=0, line_color=GRID, line_width=0.9, line_dash="dash")

    # Spot
    fig.add_vline(
        x=p.stock_price, line_color=AMBER, line_width=1.6, line_dash="dot",
        annotation_text=f"Spot  R${p.stock_price:.2f}",
        annotation_font_color=AMBER, annotation_font_size=10,
        annotation_position="top right",
    )

    # Breakevens
    for i, be in enumerate(p.breakevens[:3]):
        fig.add_vline(
            x=be, line_color=RED, line_width=1.2, line_dash="dash",
            annotation_text=f"BE{i+1}  R${be:.2f}",
            annotation_font_color=RED, annotation_font_size=10,
            annotation_position="top left" if i == 0 else "top right",
        )

    rr_txt = f"{p.risk_reward:.1f}x" if not math.isinf(p.risk_reward) else "∞"
    subtitle = (
        f"{p.underlying} · {p.name} · "
        f"DTE {p.dte}d · Vto {p.expiry} · "
        f"R/R {rr_txt} · P(lucro) {opp.prob_profit:.0%}"
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(family="Inter, sans-serif", size=11, color=TEXT),
        title=dict(
            text=subtitle,
            font=dict(size=12, color=WHITE), x=0.01,
        ),
        xaxis=dict(
            title="Preço no Vencimento (R$)",
            title_font=dict(color=TEXT, size=10),
            showgrid=True, gridcolor=GRID, zeroline=False,
            tickfont=dict(color=TEXT, size=10),
        ),
        yaxis=dict(
            title="Resultado (R$)",
            title_font=dict(color=TEXT, size=10),
            showgrid=True, gridcolor=GRID, zeroline=False,
            tickfont=dict(color=TEXT, size=10),
            tickprefix="R$",
        ),
        legend=dict(
            bgcolor=BG2, bordercolor=GRID, borderwidth=1,
            font=dict(size=10, color=TEXT), x=0.01, y=0.99,
        ),
        margin=dict(l=0, r=0, t=45, b=0),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG2, bordercolor=GRID, font_color=WHITE),
        height=height,
    )

    from uuid import uuid4
    st_mod.plotly_chart(
        fig,
        use_container_width=True,
        key=f"payoff_{uuid4().hex}"
    )

    if show_metrics:
        c1, c2, c3, c4, c5 = st_mod.columns(5)
        custo_fmt = f"R${abs(p.net_cost):,.2f}"
        c1.metric("Custo",     custo_fmt, "débito" if p.net_cost > 0 else "crédito")
        c2.metric("Ganho máx", f"R${p.max_profit:,.2f}" if not math.isinf(p.max_profit) else "∞")
        c3.metric("Perda máx", f"R${p.max_loss:,.2f}"   if not math.isinf(p.max_loss)   else "∞")
        c4.metric("R/R",       rr_txt)
        c5.metric("P(Lucro)",  f"{opp.prob_profit:.1%}")


# ── Painel de Sinais Técnicos ────────────────────────────────────────────────

def _render_technical_signals(st_mod, asset: str, data: dict) -> None:
    """Renderiza o painel de análise técnica quantificada."""
    signals = data.get("signals", [])
    overall = data.get("overall", {})
    stats   = data.get("stats", {})

    if not signals:
        st_mod.info("Dados insuficientes para análise técnica (mínimo 30 pregões).")
        return

    ov_score = overall.get("score", 50)
    ov_color = overall.get("color", "#64748B")
    ov_label = overall.get("label", "Neutro")
    price    = stats.get("price", 0)
    rsi_val  = stats.get("rsi", 0)
    atr_pct  = stats.get("atr_pct", 0)
    vol_rat  = stats.get("vol_ratio", 1)

    st_mod.markdown(
        '<div class="sec-title" style="margin-top:18px">📐 Análise Técnica Quantificada</div>',
        unsafe_allow_html=True,
    )

    # Header: score geral + métricas rápidas
    bar_w = min(int(ov_score), 100)
    st_mod.markdown(f"""
    <div style="background:#0D1421;border:1px solid #1E3A5F;border-radius:12px;padding:18px 22px;margin-bottom:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
        <div>
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:4px">{asset} · Consenso Técnico</div>
        <div style="font-size:1.6rem;font-weight:900;color:{ov_color}">{ov_label}</div>
        </div>
        <div style="display:flex;gap:20px;flex-wrap:wrap">
        <div style="text-align:center">
            <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Score</div>
            <div style="font-size:2rem;font-weight:900;color:{ov_color}">{ov_score:.0f}</div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">RSI</div>
            <div style="font-size:2rem;font-weight:900;color:{'#EF4444' if rsi_val>=70 else '#22C55E' if rsi_val<=30 else '#E2E8F0'}">{rsi_val:.1f}</div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">ATR%</div>
            <div style="font-size:2rem;font-weight:900;color:{'#EF4444' if atr_pct>4 else '#F59E0B' if atr_pct>2 else '#22C55E'}">{atr_pct:.1f}%</div>
        </div>
        <div style="text-align:center">
            <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Vol</div>
            <div style="font-size:2rem;font-weight:900;color:{'#3B82F6' if vol_rat>2 else '#E2E8F0'}">{vol_rat:.1f}×</div>
        </div>
        </div>
    </div>
    <div style="background:#1E2D42;border-radius:3px;height:4px;margin-top:14px">
        <div style="width:{bar_w}%;height:4px;border-radius:3px;background:{ov_color};transition:width 0.3s"></div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Cards por indicador
    scored_signals = [s for s in signals if s.get("score") is not None]
    info_signals   = [s for s in signals if s.get("score") is None]

    # Grid 2×2 para indicadores com score
    if scored_signals:
        pairs = [scored_signals[i:i+2] for i in range(0, len(scored_signals), 2)]
        for pair in pairs:
            cols = st_mod.columns(len(pair))
            for col, sig in zip(cols, pair):
                sc    = sig["score"]
                color = sig["color"]
                bar   = min(int(sc), 100)
                col.markdown(f"""
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;height:100%">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
        <div style="font-size:0.68rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.8px">{sig['name']}</div>
        <div style="font-size:1.1rem;font-weight:900;color:{color}">{sc:.0f}</div>
    </div>
    <div style="font-size:1.2rem;font-weight:800;color:{color};margin-bottom:6px;font-family:monospace">{sig['value']}</div>
    <div style="font-size:0.75rem;color:#475569;line-height:1.5">{sig['interpretation']}</div>
    <div style="background:#1E2D42;border-radius:2px;height:3px;margin-top:10px">
        <div style="width:{bar}%;height:3px;border-radius:2px;background:{color}"></div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Linha de informações (ATR, Volume)
    if info_signals:
        cols = st_mod.columns(len(info_signals))
        for col, sig in zip(cols, info_signals):
            col.markdown(f"""
    <div style="background:#0A0E1A;border:1px solid #1E2D42;border-radius:8px;padding:12px 14px">
    <div style="font-size:0.65rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:5px">{sig['name']}</div>
    <div style="font-size:1.0rem;font-weight:800;color:{sig['color']};margin-bottom:4px;font-family:monospace">{sig['value']}</div>
    <div style="font-size:0.72rem;color:#334155">{sig['interpretation']}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(skip_page_config: bool = False):
    try:
        import streamlit as st
    except ImportError:
        print("pip install streamlit")
        return

    import pandas as pd

    from src.utils import load_config, project_path
    from src.strategies.call_continuity_strategy import load_quant_config
    from src.options.structure_scanner import scan_all, scan_asset, scan_to_df
    from src.options.strategy_report import format_strategy_report

    # ── Page config ──
    if not skip_page_config:
        st.set_page_config(
            page_title="Radar Quant",
            page_icon="🎯",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Session state ──
    if "selected_idx" not in st.session_state:
        st.session_state.selected_idx = None

    # ── Market status ──
    is_open, clock_str, date_str = _market_status()
    mkt_cls  = "mkt-open"  if is_open else "mkt-close"
    mkt_dot  = "🟢"        if is_open else "🔴"
    mkt_text = "B3 ABERTA" if is_open else "B3 FECHADA"

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### 🎯 Radar Quant")
        st.caption("Scanner quantitativo de opções B3")
        st.markdown("---")

        cfg  = load_config()
        qcfg = load_quant_config()
        ativos_cfg = qcfg.get("ativos_permitidos", ["PETR4"])

        # ── Escopo ──
        st.markdown("**📌 Ativo**")
        modo_scan = st.radio(
            "Escopo", ["Todos os ativos", "Ativo específico"],
            label_visibility="collapsed",
        )
        selected_asset = (
            st.selectbox("Ativo", ativos_cfg, label_visibility="collapsed")
            if modo_scan == "Ativo específico" else None
        )
        top_n = st.slider("Máx. estruturas", 5, 60, 20)

        st.markdown("---")

        # ── Modo ──
        st.markdown("**⚙️ Modo Operacional**")
        modo = st.radio(
            "Modo",
            ["🛡 Conservador — risco definido, baixo/moderado",
             "⚡ Agressivo — todas as estruturas"],
            label_visibility="collapsed",
        )
        scan_mode = "conservative" if "Conservador" in modo else "normal"

        st.markdown("---")

        # ── Filtros ──
        st.markdown("**🔍 Filtros**")

        filter_status = st.multiselect(
            "Status do setup",
            ["OPERACIONAL", "ESTUDO", "DESCARTAR"],
            default=["OPERACIONAL", "ESTUDO"],
        )
        filter_types = st.multiselect(
            "Tipo de estratégia",
            ["SPREAD_ALTA", "SPREAD_BAIXA", "CONDOR", "BUTTERFLY",
             "VOLATILIDADE", "RENDA", "PROTECAO", "DIRECIONAL"],
            placeholder="Todos os tipos",
        )
        tipo_opcao = st.multiselect(
            "Tipo de opção",
            ["CALL", "PUT"],
            placeholder="CALL e PUT",
        )

        score_min = st.slider("Score mínimo", 0, 80, 30,
                              help="Setups com score abaixo serão ocultados")
        dte_range = st.slider("DTE — dias até vencimento", 5, 90, (10, 60))

        only_definido = st.checkbox("Apenas risco definido", value=True)
        no_margin     = st.checkbox("Excluir estruturas com margem", value=False)

        st.markdown("---")
        run_btn = st.button("🔄 Rodar Scanner", type="primary", use_container_width=True)

    # ── Scanner ──
    @st.cache_data(ttl=300, show_spinner="🔍 Escaneando estruturas...")
    def _run(asset, top, mode):
        db_path = project_path(cfg["database_path"])
        if not db_path.exists():
            return [], pd.DataFrame()
        con = sqlite3.connect(db_path)
        try:
            opps = (
                scan_asset(asset, con, cfg, qcfg, top=top, mode=mode)
                if asset
                else scan_all(con, cfg, qcfg, top_per_asset=5, top_total=top, mode=mode)
            )
        finally:
            con.close()
        return opps, scan_to_df(opps)

    if run_btn:
        st.cache_data.clear()
        st.session_state.selected_idx = None

    opps, df = _run(selected_asset, top_n, scan_mode)

    # ── Filtros pós-scan ──
    def _apply(opps_in):
        out = list(opps_in)
        if filter_status:
            out = [o for o in out if o.status in filter_status]
        if filter_types:
            out = [o for o in out if o.payoff.strategy_type in filter_types]
        if tipo_opcao:
            def _has_type(o):
                return any(
                    l.option_type in tipo_opcao
                    for l in o.payoff.legs
                    if l.option_type != "STOCK"
                )
            out = [o for o in out if _has_type(o)]
        if only_definido:
            out = [o for o in out if o.payoff.risk_level == "DEFINIDO"]
        if no_margin:
            out = [o for o in out if not o.payoff.requires_margin]
        out = [o for o in out if o.score >= score_min]
        out = [o for o in out if dte_range[0] <= o.payoff.dte <= dte_range[1]]
        return out

    opps = _apply(opps)

    # ── KPIs ──
    total  = len(opps)
    n_op   = sum(1 for o in opps if o.status == "OPERACIONAL")
    n_est  = sum(1 for o in opps if o.status == "ESTUDO")
    avg_sc = sum(o.score for o in opps) / total if total else 0
    avg_pp = sum(o.prob_profit for o in opps) / total if total else 0
    n_ativos = len({o.payoff.underlying for o in opps})

    # tendência dominante
    _cnd_score = {
        "ALTA_FORTE": 2, "ALTA_MODERADA": 1, "BAIXA_FORTE": -2,
        "BAIXA_MODERADA": -1, "LATERAL": 0, "ALTA_VOL": 0,
        "BAIXA_VOL": 0, "INDEFINIDO": 0,
    }
    if opps:
        tend_sum = sum(_cnd_score.get(o.market_condition.value, 0) for o in opps)
        if tend_sum >= 2:
            tend_txt, tend_color = "📈 ALTA",    "#22C55E"
        elif tend_sum <= -2:
            tend_txt, tend_color = "📉 BAIXA",   "#EF4444"
        elif tend_sum > 0:
            tend_txt, tend_color = "↗ VIÉS +",   "#86EFAC"
        elif tend_sum < 0:
            tend_txt, tend_color = "↘ VIÉS −",   "#FCA5A5"
        else:
            tend_txt, tend_color = "⬌ NEUTRO",  "#64748B"
    else:
        tend_txt, tend_color = "—", "#334155"

    # ── HEADER ──
    st.markdown(f"""
    <div class="rq-header">
    <div class="rq-header-top">
        <div>
        <div class="rq-title">🎯 <em>Radar Quant</em></div>
        <div class="rq-sub">Scanner quantitativo de opções B3 &nbsp;·&nbsp; {date_str}</div>
        </div>
        <div class="rq-meta">
        <div class="rq-clock" id="rq-clock-val">{clock_str}</div>
        <span class="rq-market {mkt_cls}">{mkt_dot} {mkt_text}</span>
        <span class="rq-pill">🎯 {n_op} setup{"s" if n_op != 1 else ""} ativos</span>
        </div>
    </div>
    </div>
    {_CLOCK_JS}
    """, unsafe_allow_html=True)

    # ── KPI STRIP ──
    _op_txt  = "oportunidade clara" if n_op == 1 else "oportunidades claras"
    _est_txt = "em monitoramento"   if n_est == 1 else "em monitoramento"
    st.markdown(f"""
    <div class="kpi-strip">
    <div class="kpi-card kc-green">
        <div class="kpi-label">🔥 Operar agora</div>
        <div class="kpi-value" style="color:#22C55E">{n_op}</div>
        <div class="kpi-sub">{_op_txt} · {n_ativos} ativo{"s" if n_ativos != 1 else ""}</div>
    </div>
    <div class="kpi-card kc-amber">
        <div class="kpi-label">⚠️ Monitorar</div>
        <div class="kpi-value" style="color:#F59E0B">{n_est}</div>
        <div class="kpi-sub">{_est_txt}</div>
    </div>
    <div class="kpi-card kc-purple">
        <div class="kpi-label">Tendência Geral</div>
        <div class="kpi-value" style="color:{tend_color};font-size:1.1rem">{tend_txt}</div>
        <div class="kpi-sub">mercado dominante</div>
    </div>
    <div class="kpi-card kc-slate">
        <div class="kpi-label">P(Lucro) Médio</div>
        <div class="kpi-value">{avg_pp:.0%}</div>
        <div class="kpi-sub">score médio {avg_sc:.0f} · {total} setups</div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    if not opps:
        st.warning("Nenhuma estrutura encontrada. Relaxe os filtros ou rode o scanner.")
        return

    # ═══════════════════════════════════════════════════════════════════════
    # TOP TRADES DO DIA
    # ═══════════════════════════════════════════════════════════════════════
    top_opps = [o for o in opps if o.status == "OPERACIONAL"][:5]

    if top_opps:
        st.markdown(
            '<div class="sec-title">🔥 Top Trades do Dia — Prontos para Operar</div>',
            unsafe_allow_html=True,
        )

        # ── #1 — HERO CARD (destaque total, largura total) ──
        st.markdown(_top_trade_hero(top_opps[0]), unsafe_allow_html=True)
        if st.button(
            f"▶ Ver detalhe completo — {top_opps[0].payoff.underlying}",
            key="tt_btn_hero",
            type="primary",
        ):
            st.session_state.selected_idx = opps.index(top_opps[0])

        # ── #2-#5 — Cards menores ──
        rest = top_opps[1:5]
        if rest:
            st.markdown(
                '<div style="font-size:0.6rem;color:#334155;text-transform:uppercase;'
                'letter-spacing:1px;margin:16px 0 10px">Outros candidatos</div>',
                unsafe_allow_html=True,
            )
            cols = st.columns(len(rest))
            for i, (col, opp) in enumerate(zip(cols, rest)):
                with col:
                    st.markdown(_top_trade_card(opp, i + 2), unsafe_allow_html=True)
                    if st.button(
                        "▶ Ver",
                        key=f"tt_btn_{i + 1}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_idx = opps.index(opp)

        # Detalhe inline ao clicar
        idx = st.session_state.selected_idx
        if idx is not None and 0 <= idx < len(opps):
            sel = opps[idx]
            st.markdown(
                f'<div class="sec-title">📋 Detalhe — {sel.payoff.underlying} · {sel.name}</div>',
                unsafe_allow_html=True,
            )
            c_left, c_right = st.columns([3, 2])
            with c_left:
                p = sel.payoff
                main_leg = next((l for l in p.legs if l.option_type != "STOCK"), None)

                st.markdown(f"### {p.underlying} · {p.name}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Score", f"{sel.score:.0f}")
                c2.metric("Status", sel.status)
                c3.metric("DTE", f"{p.dte} dias")
                c4.metric("P(Lucro)", f"{sel.prob_profit:.1%}")

                st.divider()

                a1, a2, a3 = st.columns(3)
                a1.metric("Entrada", f"R$ {main_leg.price:.4f}" if main_leg else "—")
                a2.metric("Stop", "-30%")
                a3.metric("Alvo", "+50%")

                st.divider()

                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Custo", f"R$ {abs(p.net_cost):,.2f}")
                r2.metric("Ganho Máx", f"R$ {p.max_profit:,.2f}")
                r3.metric("Perda Máx", f"R$ {p.max_loss:,.2f}")
                r4.metric("R/R", f"{p.risk_reward:.2f}x")

                st.markdown("#### Leitura")
                st.write(generate_human_report(sel)["contexto"])
                st.write(generate_human_report(sel)["leitura"])

                st.markdown("#### Estratégia")
                st.write(generate_human_report(sel)["estrategia"])

                st.markdown("#### Quando ganha")
                st.success(p.best_scenario)

                st.markdown("#### Quando perde")
                st.error(p.worst_scenario)
            with c_right:
                _payoff_chart(sel, st, height=340, show_metrics=False)
                st.markdown(_detail_html(sel), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO DE GRÁFICOS — visível imediatamente na página principal
    # ═══════════════════════════════════════════════════════════════════════
    if top_opps:
        hero_opp = top_opps[0]
        from src.options.chart_engine import render_chart, HAS_PLOTLY

        st.markdown(
            '<div class="sec-title">📊 Análise Técnica & Payoff — Top Trade</div>',
            unsafe_allow_html=True,
        )

        col_price, col_payoff = st.columns([3, 2])

        with col_price:
            if HAS_PLOTLY:
                db_path_c = project_path(cfg["database_path"])
                try:
                    _con_c = sqlite3.connect(db_path_c)
                    fig_price = render_chart(
                        hero_opp.payoff.underlying, _con_c, hero_opp, 120
                    )
                    _con_c.close()
                except Exception:
                    fig_price = None
                if fig_price is not None:
                    fig_price.update_layout(height=460)
                    st.plotly_chart(fig_price, use_container_width=True)
                else:
                    st.info(f"Sem dados OHLCV para {hero_opp.payoff.underlying}.")
            else:
                st.warning("Instale plotly para ver gráficos de preço.")

        with col_payoff:
            _payoff_chart(hero_opp, st, height=320, show_metrics=False)
            # Métricas compactas abaixo do payoff
            p_h = hero_opp.payoff
            rr_h = f"{p_h.risk_reward:.1f}x" if not math.isinf(p_h.risk_reward) else "∞"
            st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">
    <div style="background:#0D1421;border:1px solid #1E3A5F;border-radius:8px;padding:10px 14px">
        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">P(Lucro)</div>
        <div style="font-size:1.4rem;font-weight:900;color:#22C55E">{hero_opp.prob_profit:.0%}</div>
    </div>
    <div style="background:#0D1421;border:1px solid #1E3A5F;border-radius:8px;padding:10px 14px">
        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">R / R</div>
        <div style="font-size:1.4rem;font-weight:900;color:#3B82F6">{rr_h}</div>
    </div>
    <div style="background:#052e16;border:1px solid #166534;border-radius:8px;padding:10px 14px">
        <div style="font-size:0.6rem;color:#166534;text-transform:uppercase;letter-spacing:1px">Ganho Máx</div>
        <div style="font-size:1.1rem;font-weight:900;color:#22C55E">{"R${:,.2f}".format(p_h.max_profit) if not math.isinf(p_h.max_profit) else "∞"}</div>
    </div>
    <div style="background:#1c0909;border:1px solid #7f1d1d;border-radius:8px;padding:10px 14px">
        <div style="font-size:0.6rem;color:#7f1d1d;text-transform:uppercase;letter-spacing:1px">Perda Máx</div>
        <div style="font-size:1.1rem;font-weight:900;color:#EF4444">{"R${:,.2f}".format(p_h.max_loss) if not math.isinf(p_h.max_loss) else "∞"}</div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Telegram button (sidebar) ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📲 Alertas Telegram**")
        from src.notifications.telegram_bot import telegram_disponivel, testar_conexao, send_top_setups as _tg_send
        tg_ok = telegram_disponivel()
        if tg_ok:
            st.caption("✅ Configurado via news_hunter")
        else:
            st.caption("⚠️ Configure no news_hunter/config.py")

        tg_score = st.slider("Score mín. p/ alerta", 50, 90, 70, key="tg_score")

        if st.button("🔔 Enviar top setups", key="tg_send",
                     use_container_width=True, disabled=not tg_ok):
            with st.spinner("Enviando..."):
                results = _tg_send(opps, min_score=tg_score)
            sent = sum(1 for r in results if r["sent"])
            st.success(f"✅ {sent} alerta(s) enviados")

        if st.button("🧪 Testar conexão", key="tg_test",
                     use_container_width=True, disabled=not tg_ok):
            ok, msg = testar_conexao()
            (st.success if ok else st.error)(msg)

    # ═══════════════════════════════════════════════════════════════════════
    # TABS
    # ═══════════════════════════════════════════════════════════════════════
    tab_opp, tab_chart, tab_payoff, tab_heatmap, tab_risk, tab_flow_ml, tab_backtest, tab_exec, tab_news, tab_rank, tab_report = st.tabs([
        "📋 Setups", "📊 Gráfico", "📈 Payoff",
        "🗺 Heatmap", "⚡ Risco",
        "🤖 Fluxo & ML", "⚙️ Backtest", "🎯 Plano Operacional",
        "📰 Notícias", "📊 Ranking", "📄 Relatório",
    ])

    # ── TAB 1: Todos os Setups ──
    with tab_opp:
        any_shown = False

        # OPERACIONAL — grid 3 colunas com compact card
        op_opps = [o for o in opps if o.status == "OPERACIONAL"]
        if op_opps:
            any_shown = True
            st.markdown(
                f'<div class="sec-title">✅ Operacional — prontos para operar ({len(op_opps)})</div>',
                unsafe_allow_html=True,
            )
            N_COLS = 3
            rows = [op_opps[i:i + N_COLS] for i in range(0, len(op_opps), N_COLS)]
            for row in rows:
                cols = st.columns(N_COLS)
                for col, opp_g in zip(cols, row):
                    with col:
                        st.html(_compact_card(opp_g))
                        with st.expander("📊 Detalhe completo", expanded=False):
                            st.markdown(_detail_html(opp_g), unsafe_allow_html=True)
                            _payoff_chart(opp_g, st, height=280, show_metrics=False)

        # ESTUDO — grid 2 colunas
        est_opps = [o for o in opps if o.status == "ESTUDO"]
        if est_opps:
            any_shown = True
            st.markdown(
                f'<div class="sec-title">📋 Em Estudo — monitorar ({len(est_opps)})</div>',
                unsafe_allow_html=True,
            )
            rows_est = [est_opps[i:i + 2] for i in range(0, len(est_opps), 2)]
            for row in rows_est:
                cols = st.columns(2)
                for col, opp_g in zip(cols, row):
                    with col:
                        st.html(_compact_card(opp_g))

        # DESCARTAR — lista compacta
        desc_opps = [o for o in opps if o.status == "DESCARTAR"]
        if desc_opps:
            any_shown = True
            with st.expander(f"❌ Descartar — evitar ({len(desc_opps)})", expanded=False):
                for opp_g in desc_opps:
                    st.html(_compact_card(opp_g))

        if not any_shown:
            st.info("Nenhuma oportunidade com os filtros atuais.")

    # ── TAB 2: Gráfico profissional ──────────────────────────────────────────
    with tab_chart:
        from src.options.chart_engine import render_chart, load_ohlcv, HAS_PLOTLY
        from src.quant.technical_signals import compute_signals

        if not HAS_PLOTLY:
            st.warning("Instale plotly: `pip install plotly`")
        else:
            ativos_disponiveis = sorted({o.payoff.underlying for o in opps})
            ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 1, 1])
            with ctrl1:
                chart_asset = st.selectbox("Ativo", ativos_disponiveis, key="chart_asset")
            with ctrl2:
                chart_days = st.select_slider(
                    "Período (pregões)", [60, 120, 252, 504], value=252, key="chart_days",
                )
            with ctrl3:
                sync_setup = st.checkbox("Overlay setup", value=True, key="chart_sync")
            with ctrl4:
                show_payoff_tab = st.checkbox("Payoff lado a lado", value=True, key="chart_payoff")

            setup_for_chart = None
            if sync_setup:
                matching = [o for o in opps if o.payoff.underlying == chart_asset]
                if matching:
                    setup_for_chart = max(matching, key=lambda o: o.score)

            db_path = project_path(cfg["database_path"])
            con_chart = sqlite3.connect(db_path)
            try:
                fig_chart = render_chart(chart_asset, con_chart, setup_for_chart, chart_days)
                df_ohlcv  = load_ohlcv(chart_asset, con_chart, days=chart_days)
            finally:
                con_chart.close()

            if show_payoff_tab and setup_for_chart:
                col_ch, col_pf = st.columns([3, 2])
                with col_ch:
                    if fig_chart is None:
                        st.info(f"Sem dados OHLCV para {chart_asset} no banco.")
                    else:
                        fig_chart.update_layout(height=520)
                        st.plotly_chart(fig_chart, use_container_width=True)
                with col_pf:
                    st.markdown(
                        f'<div class="sec-title" style="margin-top:0">📈 Payoff — {setup_for_chart.payoff.underlying}</div>',
                        unsafe_allow_html=True,
                    )
                    _payoff_chart(setup_for_chart, st, height=320, show_metrics=True)
                    st.markdown(_detail_html(setup_for_chart), unsafe_allow_html=True)
            else:
                if fig_chart is None:
                    st.info(f"Sem dados OHLCV para {chart_asset} no banco.")
                else:
                    fig_chart.update_layout(height=620)
                    st.plotly_chart(fig_chart, use_container_width=True)
                if setup_for_chart:
                    st.markdown(_compact_card(opp), unsafe_allow_html=True)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Score", f"{opp.score:.0f}")
                    m2.metric("P(Lucro)", f"{opp.prob_profit:.0%}")
                    m3.metric("R/R", f"{opp.payoff.risk_reward:.1f}x")
                    m4.metric("DTE", f"{opp.payoff.dte}d")
                    with st.expander("📋 Leitura operacional", expanded=True):

                        r = generate_human_report(opp)

                        st.markdown("#### 🌍 Contexto")
                        st.info(r["contexto"])

                        st.markdown("#### 📈 Leitura")
                        st.success(r["leitura"])

                        st.markdown("#### 🎯 Estratégia")
                        st.warning(r["estrategia"])

            # ── Painel de Sinais Técnicos ──────────────────────────────────
            signals_data = compute_signals(df_ohlcv)
            _render_technical_signals(st, chart_asset, signals_data)

    # ── TAB 3: Payoff interativo ──
    with tab_payoff:
        def _label(i):
            o = opps[i]
            return (f"{_STATUS_ICON.get(o.status,'')} #{o.rank} "
                    f"{o.payoff.underlying} — {o.name} "
                    f"(Score {o.score:.0f})")

        idx_pay = st.selectbox("Estrutura", range(len(opps)), format_func=_label)
        opp_sel = opps[idx_pay]
        p_sel   = opp_sel.payoff

        dir_text, dir_cls = _DIR_MAP.get(p_sel.strategy_type, ("NEUTRO", "b-lat"))
        cat_bg, cat_fg    = _CAT_STYLE.get(p_sel.risk_category, ("#1E2D42", "#94A3B8"))
        status_badge      = _STATUS_BADGE.get(opp_sel.status, "b-est")
        status_icon       = _STATUS_ICON.get(opp_sel.status, "")

        st.markdown(f"""
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
    <span class="badge {status_badge}">{status_icon} {opp_sel.status}</span>
    <span class="badge {dir_cls}">{dir_text}</span>
    <span style="font-size:0.72rem;font-weight:700;background:{cat_bg};color:{cat_fg};
                padding:2px 9px;border-radius:10px">{p_sel.risk_category}</span>
    <span style="font-size:0.78rem;color:#334155;font-style:italic">{opp_sel.why_ranked}</span>
    </div>
""", unsafe_allow_html=True)

        col_pf, col_det = st.columns([3, 2])
        with col_pf:
            _payoff_chart(opp_sel, st, height=420, show_metrics=True)
        with col_det:
            st.markdown(_detail_html(opp_sel), unsafe_allow_html=True)

    # ── TAB 4: Heatmap de ativos ─────────────────────────────────────────────
    with tab_heatmap:
        try:
            import plotly.express as px
            import plotly.graph_objects as go

            # Agrega dados por ativo
            from collections import defaultdict
            _agg: dict = defaultdict(lambda: {
                "scores": [], "n_op": 0, "n_est": 0,
                "directions": [], "prob": [], "hv": [],
            })
            for _o in opps:
                _a = _o.payoff.underlying
                _agg[_a]["scores"].append(_o.score)
                _agg[_a]["prob"].append(_o.prob_profit)
                _agg[_a]["hv"].append(_o.hv)
                _agg[_a]["directions"].append(_o.payoff.strategy_type)
                if _o.status == "OPERACIONAL":
                    _agg[_a]["n_op"] += 1
                elif _o.status == "ESTUDO":
                    _agg[_a]["n_est"] += 1

            _rows = []
            for _asset, _d in _agg.items():
                avg_sc = sum(_d["scores"]) / len(_d["scores"])
                avg_pp = sum(_d["prob"]) / len(_d["prob"])
                avg_hv = sum(_d["hv"]) / len(_d["hv"]) if _d["hv"] else 0
                n_tot  = len(_d["scores"])

                _alta  = sum(1 for x in _d["directions"] if "ALTA" in x or x == "DIRECIONAL")
                _baixa = sum(1 for x in _d["directions"] if "BAIXA" in x)
                if _alta > _baixa:
                    _dom, _col = "ALTA", avg_sc
                elif _baixa > _alta:
                    _dom, _col = "BAIXA", -avg_sc
                else:
                    _dom, _col = "LATERAL", 0.0

                _rows.append({
                    "Ativo":    _asset,
                    "Setups":   n_tot,
                    "Op":       _d["n_op"],
                    "Score":    round(avg_sc, 1),
                    "P(Lucro)": f"{avg_pp:.0%}",
                    "Vol":      f"{avg_hv:.1%}",
                    "Direção":  _dom,
                    "_color":   _col,
                })
            _rows.sort(key=lambda r: r["_color"], reverse=True)

            import pandas as _pd
            _df = _pd.DataFrame(_rows)

            # ── Treemap (heatmap visual) ──────────────────────────────────
            st.markdown(
                '<div class="sec-title">🗺 Heatmap — Visão Macro do Mercado</div>',
                unsafe_allow_html=True,
            )

            _fig_heat = px.treemap(
                _df,
                path=["Ativo"],
                values="Setups",
                color="_color",
                color_continuous_scale=["#7f1d1d", "#1E2D42", "#166534"],
                color_continuous_midpoint=0,
                custom_data=["Score", "P(Lucro)", "Vol", "Direção", "Op"],
                hover_name="Ativo",
            )
            _fig_heat.update_traces(
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Score médio: %{customdata[0]}<br>"
                    "P(Lucro): %{customdata[1]}<br>"
                    "Vol hist: %{customdata[2]}<br>"
                    "Direção: %{customdata[3]}<br>"
                    "Operacional: %{customdata[4]}<extra></extra>"
                ),
                texttemplate="<b>%{label}</b><br>%{customdata[0]}",
                textfont=dict(size=14, color="#F1F5F9"),
            )
            _fig_heat.update_layout(
                paper_bgcolor="#080D17",
                plot_bgcolor="#111827",
                font=dict(family="Inter, sans-serif", color="#94A3B8"),
                margin=dict(l=0, r=0, t=10, b=0),
                height=440,
                coloraxis_showscale=False,
            )
            st.plotly_chart(_fig_heat, use_container_width=True)

            # ── Tabela de ativos ──────────────────────────────────────────
            st.markdown(
                '<div class="sec-title">📊 Ranking por Ativo</div>',
                unsafe_allow_html=True,
            )
            _display = _df.drop(columns=["_color"]).rename(columns={"Op": "Operacional"})
            _display = _display.sort_values("Score", ascending=False).reset_index(drop=True)
            st.dataframe(
                _display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score":    st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                    "Setups":   st.column_config.NumberColumn("Setups"),
                    "Operacional": st.column_config.NumberColumn("Operacional"),
                },
            )

        except Exception as _e:
            st.error(f"Erro no heatmap: {_e}")

        # ── Análise Quantitativa de Opções ────────────────────────────────
        st.markdown(
            '<div class="sec-title">📉 Análise Quantitativa — Volatilidade & Greeks</div>',
            unsafe_allow_html=True,
        )
        try:
            from src.options.vol_analysis import (
                compute_iv_stats, build_iv_smile_chart,
                build_vol_cone_chart, build_term_structure_chart,
                build_greeks_table,
            )
            from src.options.options_chain import build_chain
            from src.options.chart_engine import load_ohlcv

            _vol_ativos = sorted({o.payoff.underlying for o in opps})
            _vol_asset  = st.selectbox("Ativo para análise de vol", _vol_ativos, key="vol_asset")

            _con_vol = sqlite3.connect(project_path(cfg["database_path"]))
            try:
                _chain_vol = build_chain(
                    _con_vol, _vol_asset, qcfg,
                    int(qcfg.get("min_dte", 5)), int(qcfg.get("max_dte", 90)),
                    float(qcfg.get("min_volume_opcao", 1000)),
                    int(qcfg.get("min_negocios_opcao", 1)),
                )
                _prices_vol = load_ohlcv(_vol_asset, _con_vol, days=252)
            finally:
                _con_vol.close()

            if len(_chain_vol) == 0:
                st.info(f"Sem cadeia de opções líquidas para {_vol_asset}.")
            else:
                # ── KPIs de IV ────────────────────────────────────────────
                _ivs = compute_iv_stats(_chain_vol, _prices_vol)
                _iv_atm  = _ivs["iv_atm"]
                _hv21    = _ivs["hv_21"]
                _ivhv    = _ivs["iv_hv_spread"]
                _ivr     = _ivs["iv_rank"]
                _ivp     = _ivs["iv_percentile"]
                _skew    = _ivs["skew_25d"]

                _ivhv_color = "#EF4444" if _ivhv > 0.05 else "#F59E0B" if _ivhv > 0 else "#22C55E"
                _skew_color = "#EF4444" if (not math.isnan(_skew) and _skew > 0.03) else "#64748B"

                st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:18px">
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;text-align:center;border-top:3px solid #3B82F6">
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1px">IV ATM</div>
        <div style="font-size:1.5rem;font-weight:900;color:#3B82F6">{_iv_atm:.1%}</div>
        <div style="font-size:0.65rem;color:#475569">volatilidade implícita</div>
    </div>
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;text-align:center;border-top:3px solid #22C55E">
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1px">HV 21d</div>
        <div style="font-size:1.5rem;font-weight:900;color:#22C55E">{_hv21:.1%}</div>
        <div style="font-size:0.65rem;color:#475569">vol histórica</div>
    </div>
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;text-align:center;border-top:3px solid {_ivhv_color}">
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1px">IV − HV</div>
        <div style="font-size:1.5rem;font-weight:900;color:{_ivhv_color}">{_ivhv:+.1%}</div>
        <div style="font-size:0.65rem;color:#475569">prêmio de vol</div>
    </div>
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;text-align:center;border-top:3px solid #7C3AED">
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1px">IV Rank</div>
        <div style="font-size:1.5rem;font-weight:900;color:#7C3AED">{"N/A" if math.isnan(_ivr) else f"{_ivr:.0f}"}</div>
        <div style="font-size:0.65rem;color:#475569">vs 1 ano (0–100)</div>
    </div>
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;text-align:center;border-top:3px solid #F59E0B">
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1px">IV %ile</div>
        <div style="font-size:1.5rem;font-weight:900;color:#F59E0B">{"N/A" if math.isnan(_ivp) else f"{_ivp:.0f}"}</div>
        <div style="font-size:0.65rem;color:#475569">% do tempo abaixo</div>
    </div>
    <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;text-align:center;border-top:3px solid {_skew_color}">
        <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Skew 25Δ</div>
        <div style="font-size:1.5rem;font-weight:900;color:{_skew_color}">{"N/A" if math.isnan(_skew) else f"{_skew:+.1%}"}</div>
        <div style="font-size:0.65rem;color:#475569">put IV − call IV</div>
    </div>
    </div>
    """, unsafe_allow_html=True)

                # ── Gráficos ──────────────────────────────────────────────
                _col_smile, _col_cone = st.columns(2)

                with _col_smile:
                    _expiries = sorted({r.expiry for r in list(_chain_vol.calls) + list(_chain_vol.puts)
                                        if not math.isnan(r.iv_implied)})
                    if _expiries:
                        _sel_exp = st.selectbox("Vencimento para IV Smile", _expiries, key="vol_exp")
                        _fig_smile = build_iv_smile_chart(_chain_vol, _sel_exp)
                        if _fig_smile:
                            st.plotly_chart(_fig_smile, use_container_width=True)
                        else:
                            st.info("Dados insuficientes para o IV Smile.")

                with _col_cone:
                    _fig_cone = build_vol_cone_chart(_prices_vol, _chain_vol)
                    if _fig_cone:
                        st.plotly_chart(_fig_cone, use_container_width=True)
                    else:
                        st.info("Histórico insuficiente para o Volatility Cone (mín. 63 pregões).")

                # Term structure
                _fig_ts = build_term_structure_chart(_chain_vol)
                if _fig_ts:
                    st.plotly_chart(_fig_ts, use_container_width=True)

                # Greeks table
                _greeks_df = build_greeks_table(_chain_vol)
                if not _greeks_df.empty:
                    st.markdown(
                        '<div class="sec-title" style="margin-top:10px">⚙️ Greeks — Cadeia Completa</div>',
                        unsafe_allow_html=True,
                    )
                    _greeks_tipo = st.radio(
                        "Filtrar tipo", ["Todos", "CALL", "PUT"],
                        horizontal=True, key="greeks_tipo",
                    )
                    _greeks_show = (
                        _greeks_df if _greeks_tipo == "Todos"
                        else _greeks_df[_greeks_df["Tipo"] == _greeks_tipo]
                    )
                    st.dataframe(
                        _greeks_show,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "IV (%)":  st.column_config.ProgressColumn("IV (%)",  min_value=0, max_value=200, format="%.1f%%"),
                            "Delta":   st.column_config.NumberColumn("Delta",   format="%.3f"),
                            "Gamma":   st.column_config.NumberColumn("Gamma",   format="%.5f"),
                            "Theta/d": st.column_config.NumberColumn("Theta/d", format="%.4f"),
                            "Vega/1%": st.column_config.NumberColumn("Vega/1%", format="%.4f"),
                            "Liq":     st.column_config.ProgressColumn("Liq",    min_value=0, max_value=100, format="%.0f"),
                        },
                    )

        except Exception as _ev:
            st.error(f"Erro na análise de vol: {_ev}")

    # ── TAB 5: Painel de Risco ────────────────────────────────────────────────
    with tab_risk:
        st.markdown(
            '<div class="sec-title">⚡ Painel de Risco — Exposição Simulada</div>',
            unsafe_allow_html=True,
        )

        # Parâmetros
        r_col1, r_col2 = st.columns([1, 3])
        with r_col1:
            capital = st.number_input(
                "Capital simulado (R$)", min_value=1_000, max_value=10_000_000,
                value=50_000, step=5_000, key="risk_capital",
            )
            risco_pct = st.slider(
                "Risco por trade (%)", 0.5, 5.0, 1.0, 0.5, key="risk_pct",
            ) / 100

        with r_col2:
            op_list = [o for o in opps if o.status == "OPERACIONAL"]
            n_trades      = len(op_list)
            risco_trade   = capital * risco_pct
            risco_total   = risco_trade * n_trades
            risco_pct_tot = risco_total / capital if capital else 0

            _maxl = [o.payoff.max_loss for o in op_list if not math.isinf(o.payoff.max_loss)]
            perda_max_total = sum(_maxl)
            perda_media     = perda_max_total / len(_maxl) if _maxl else 0

            avg_rr   = sum(o.payoff.risk_reward for o in op_list if not math.isinf(o.payoff.risk_reward)) / n_trades if n_trades else 0
            avg_prob = sum(o.prob_profit for o in op_list) / n_trades if n_trades else 0
            # Kelly simplificado: f = p - (1-p)/R
            kelly    = avg_prob - (1 - avg_prob) / avg_rr if avg_rr > 0 else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Trades ativos",      n_trades)
            c2.metric("Risco / trade",      f"R${risco_trade:,.0f}", f"{risco_pct:.1%}")
            c3.metric("Risco total",        f"R${risco_total:,.0f}", f"{risco_pct_tot:.1%} capital")
            c4.metric("Kelly fraction",     f"{max(kelly,0):.1%}")
            c5.metric("R/R médio",          f"{avg_rr:.1f}x")

        if op_list:
            import plotly.graph_objects as go_r

            # Exposição por ativo
            st.markdown(
                '<div class="sec-title">Exposição por Ativo</div>',
                unsafe_allow_html=True,
            )
            from collections import Counter
            _exp: dict = {}
            for _o in op_list:
                _a = _o.payoff.underlying
                if not math.isinf(_o.payoff.max_loss):
                    _exp[_a] = _exp.get(_a, 0) + _o.payoff.max_loss

            _exp_items = sorted(_exp.items(), key=lambda x: x[1], reverse=True)
            _fig_exp = go_r.Figure(go_r.Bar(
                x=[i[0] for i in _exp_items],
                y=[i[1] for i in _exp_items],
                marker_color="#EF4444",
                marker_line_width=0,
                opacity=0.85,
                text=[f"R${v:,.0f}" for _, v in _exp_items],
                textposition="outside",
                textfont=dict(color="#94A3B8", size=10),
            ))
            _fig_exp.update_layout(
                paper_bgcolor="#080D17", plot_bgcolor="#111827",
                font=dict(color="#64748B", family="Inter, sans-serif"),
                xaxis=dict(showgrid=False, tickfont=dict(color="#94A3B8")),
                yaxis=dict(showgrid=True, gridcolor="#1E2D42", tickprefix="R$", tickfont=dict(color="#475569")),
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
            )
            st.plotly_chart(_fig_exp, use_container_width=True)

            # Distribuição direcional
            _dir_dist_col, _score_dist_col = st.columns(2)
            with _dir_dist_col:
                st.markdown(
                    '<div class="sec-title">Distribuição Direcional</div>',
                    unsafe_allow_html=True,
                )
                _dir_cnt: dict = {}
                for _o in op_list:
                    _k = _DIR_MAP.get(_o.payoff.strategy_type, ("OUTRO", ""))[0]
                    _dir_cnt[_k] = _dir_cnt.get(_k, 0) + 1
                _fig_dir = go_r.Figure(go_r.Pie(
                    labels=list(_dir_cnt.keys()),
                    values=list(_dir_cnt.values()),
                    hole=0.55,
                    textfont=dict(size=11, color="#E2E8F0"),
                    marker=dict(colors=["#22C55E", "#EF4444", "#3B82F6", "#F59E0B", "#7C3AED", "#06B6D4"]),
                ))
                _fig_dir.update_layout(
                    paper_bgcolor="#080D17", showlegend=True,
                    legend=dict(font=dict(color="#64748B", size=10), bgcolor="#080D17"),
                    margin=dict(l=0, r=0, t=0, b=0), height=220,
                )
                st.plotly_chart(_fig_dir, use_container_width=True)

            with _score_dist_col:
                st.markdown(
                    '<div class="sec-title">Distribuição de Scores</div>',
                    unsafe_allow_html=True,
                )
                _scores = [_o.score for _o in op_list]
                _fig_sc = go_r.Figure(go_r.Histogram(
                    x=_scores, nbinsx=10,
                    marker_color="#3B82F6", marker_line_width=0, opacity=0.8,
                ))
                _fig_sc.update_layout(
                    paper_bgcolor="#080D17", plot_bgcolor="#111827",
                    font=dict(color="#64748B"),
                    xaxis=dict(showgrid=False, tickfont=dict(color="#94A3B8"), title="Score"),
                    yaxis=dict(showgrid=True, gridcolor="#1E2D42", tickfont=dict(color="#475569")),
                    margin=dict(l=0, r=0, t=0, b=0), height=220,
                    bargap=0.1,
                )
                st.plotly_chart(_fig_sc, use_container_width=True)

    # ── TAB 6: Fluxo & ML ────────────────────────────────────────────────────
    with tab_flow_ml:
        from src.options.flow_engine import compute_flow_from_db, flow_html
        from src.options.ml_ranking import train_model as ml_train, predict as ml_predict, predict_html

        st.markdown('<div class="sec-title">🌊 Fluxo de Mercado + 🤖 Ranking ML por Setup</div>', unsafe_allow_html=True)

        # Treina modelo com os setups disponíveis (label proxy)
        @st.cache_data(ttl=600, show_spinner="Treinando modelo ML...")
        def _train_ml(n_opps: int):
            if n_opps < 5:
                return None
            return ml_train(opps)

        ml_model = _train_ml(len(opps))

        # Seletor de ativo para fluxo
        ativos_flow = sorted({o.payoff.underlying for o in opps})
        flow_asset  = st.selectbox("Ativo para análise de fluxo", ativos_flow, key="flow_asset")

        db_path = project_path(cfg["database_path"])
        con_flow = sqlite3.connect(db_path)
        try:
            flow_result = compute_flow_from_db(flow_asset, con_flow)
        finally:
            con_flow.close()

        st.markdown(flow_html(flow_result), unsafe_allow_html=True)

        st.markdown('<div class="sec-title" style="margin-top:24px">🤖 Probabilidade ML por Setup</div>', unsafe_allow_html=True)

        setups_flow = [o for o in opps if o.payoff.underlying == flow_asset] or opps[:5]
        for opp in setups_flow[:6]:

            pred = ml_predict(ml_model, opp) if ml_model else ml_predict(None, opp)

            col_l, col_r = st.columns([3, 2])
        
        with col_l:
            st.markdown(_compact_card(opp), unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)

            m1.metric("Score", f"{opp.score:.0f}")
            m2.metric("P(Lucro)", f"{opp.prob_profit:.0%}")
            m3.metric("R/R", f"{opp.payoff.risk_reward:.1f}x")
            m4.metric("DTE", f"{opp.payoff.dte}d")
            with st.expander("📋 Leitura operacional", expanded=True):

                r = generate_human_report(opp)

                st.markdown("#### 🌍 Contexto")
                st.info(r["contexto"])

                st.markdown("#### 📈 Leitura")
                st.success(r["leitura"])

                st.markdown("#### 🎯 Estratégia")
                st.warning(r["estrategia"])
            with col_r:
                st.markdown(predict_html(pred), unsafe_allow_html=True)

            st.divider()
            pred = ml_predict(ml_model, opp) if ml_model else ml_predict(None, opp)

            col_l, col_r = st.columns([3, 2])
            with col_l:
                st.markdown(_compact_card(opp), unsafe_allow_html=True)
                with st.expander("📋 Leitura operacional", expanded=True):

                    r = generate_human_report(opp)

                    st.markdown("#### 🌍 Contexto")
                    st.info(r["contexto"])

                    st.markdown("#### 📈 Leitura")
                    st.success(r["leitura"])

                    st.markdown("#### 🎯 Estratégia")
                    st.warning(r["estrategia"])
            with col_r:
                st.markdown(predict_html(pred), unsafe_allow_html=True)

    # ── TAB 5: Backtest ──────────────────────────────────────────────────────
    with tab_backtest:
        from src.quant.backtester import BacktestEngine, BacktestConfig

        st.markdown('<div class="sec-title">⚙️ Backtest — Simulação Histórica</div>', unsafe_allow_html=True)

        # Configuração
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            bt_capital  = st.number_input("Capital inicial (R$)", 5_000, 500_000, 10_000, 1_000)
            bt_risk_pct = st.slider("Risco por trade (%)", 0.1, 3.0, 0.5, 0.1) / 100
        with col_b:
            bt_stop_pct    = st.slider("Stop (%)", 10, 60, 30) / 100
            bt_target1_pct = st.slider("Alvo 1 (%)", 20, 100, 50) / 100
        with col_c:
            bt_target2_pct = st.slider("Alvo 2 (%)", 50, 200, 100) / 100
            bt_max_days    = st.slider("Dias máx no trade", 10, 60, 30)

        run_bt = st.button("▶ Rodar Backtest", type="primary")

        if run_bt:
            bt_cfg = BacktestConfig(
                initial_capital=bt_capital,
                risk_pct=bt_risk_pct,
                stop_pct=bt_stop_pct,
                target1_pct=bt_target1_pct,
                target2_pct=bt_target2_pct,
                max_holding_days=bt_max_days,
            )
            engine = BacktestEngine(bt_cfg)

            # Gera sinais a partir dos setups filtrados
            signals_list = []
            for o in opps:
                main_leg = next((l for l in o.payoff.legs if l.option_type != "STOCK"), None)
                if main_leg:
                    signals_list.append({
                        "date":         datetime.now().strftime("%Y-%m-%d"),
                        "ticker":       main_leg.ticker,
                        "underlying":   o.payoff.underlying,
                        "option_type":  main_leg.option_type,
                        "entry_price":  main_leg.price,
                        "score":        o.score,
                        "dte":          o.payoff.dte,
                    })

            if not signals_list:
                st.warning("Nenhum sinal gerado. Rode o scanner primeiro.")
            else:
                signals_df = pd.DataFrame(signals_list)
                db_path    = project_path(cfg["database_path"])
                con_bt     = sqlite3.connect(db_path)
                try:
                    # Carrega preços históricos para cada ativo
                    ativos_bt = signals_df["underlying"].unique().tolist()
                    price_data = {}
                    for at in ativos_bt:
                        qry = """
                            SELECT trade_date, close, high, low
                            FROM cotahist_daily
                            WHERE ticker = ? AND market_type = '010'
                            ORDER BY trade_date
                        """
                        pf = pd.read_sql(qry, con_bt, params=(at,))
                        if not pf.empty:
                            price_data[at] = pf
                finally:
                    con_bt.close()

                engine.run_from_signals(signals_df, price_data)
                summ   = engine.summary()
                trades = engine.trades_df()
                equity = engine.equity_curve()

                if "message" in summ:
                    st.info(summ["message"])
                else:
                    # KPIs do backtest
                    st.markdown(f"""
                        <div class="kpi-strip" style="margin-top:16px">
                        <div class="kpi-card kc-blue">
                            <div class="kpi-label">Trades</div>
                            <div class="kpi-value">{summ.get('total_trades', 0)}</div>
                        </div>
                        <div class="kpi-card {'kc-green' if summ.get('win_rate',0)>=0.5 else 'kc-amber'}">
                            <div class="kpi-label">Win Rate</div>
                            <div class="kpi-value" style="color:{'#22C55E' if summ.get('win_rate',0)>=0.5 else '#F59E0B'}">{summ.get('win_rate',0):.1%}</div>
                        </div>
                        <div class="kpi-card kc-purple">
                            <div class="kpi-label">Sharpe</div>
                            <div class="kpi-value">{summ.get('sharpe',0):.2f}</div>
                        </div>
                        <div class="kpi-card kc-amber">
                            <div class="kpi-label">Max Drawdown</div>
                            <div class="kpi-value" style="color:#EF4444">{summ.get('max_drawdown',0):.1%}</div>
                        </div>
                        <div class="kpi-card {'kc-green' if summ.get('total_pnl',0)>=0 else 'kc-slate'}">
                            <div class="kpi-label">P&L Total</div>
                            <div class="kpi-value" style="color:{'#22C55E' if summ.get('total_pnl',0)>=0 else '#EF4444'}">R${summ.get('total_pnl',0):,.0f}</div>
                        </div>
                        <div class="kpi-card kc-blue">
                            <div class="kpi-label">Capital Final</div>
                            <div class="kpi-value">R${summ.get('final_capital',bt_capital):,.0f}</div>
                        </div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Curva de equity (Plotly)
                    try:
                        import plotly.graph_objects as go
                        fig_eq = go.Figure()
                        fig_eq.add_trace(go.Scatter(
                            y=equity.values,
                            mode="lines",
                            name="Equity",
                            line=dict(color="#3B82F6", width=2),
                            fill="tozeroy",
                            fillcolor="rgba(59,130,246,0.07)",
                        ))
                        fig_eq.add_hline(
                            y=bt_capital, line_color="#334155",
                            line_dash="dash", line_width=1,
                            annotation_text="Capital inicial",
                            annotation_font_color="#475569",
                        )
                        fig_eq.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="#080D17",
                            plot_bgcolor="#111827",
                            height=300,
                            margin=dict(l=0, r=0, t=10, b=0),
                            yaxis=dict(tickprefix="R$", gridcolor="#1E2D42"),
                            xaxis=dict(title="Trade #", gridcolor="#1E2D42"),
                            showlegend=False,
                        )
                        st.plotly_chart(fig_eq, use_container_width=True)
                    except ImportError:
                        st.line_chart(equity)

                    # Tabela de trades
                    if not trades.empty:
                        st.markdown('<div class="sec-title">Trades simulados</div>', unsafe_allow_html=True)

                        def _bt_style(row):
                            c = [""] * len(row)
                            if "exit_reason" in row.index:
                                idx_l = list(row.index)
                                reason = row.get("exit_reason", "")
                                color = (
                                    "#052e16" if "ALVO" in str(reason) else
                                    "#1c0909" if reason == "STOP" else ""
                                )
                                if color:
                                    c[idx_l.index("exit_reason")] = f"background:{color}"
                            if "net_pnl" in row.index:
                                idx_l = list(row.index)
                                pnl = row.get("net_pnl", 0)
                                c[idx_l.index("net_pnl")] = (
                                    "color:#22C55E;font-weight:700" if pnl > 0 else
                                    "color:#EF4444;font-weight:700"
                                )
                            return c

                        cols_bt = ["date_entry","date_exit","ticker","underlying",
                                   "entry_price","exit_price","contracts",
                                   "gross_pnl","net_pnl","return_pct","exit_reason"]
                        cols_bt_ok = [c for c in cols_bt if c in trades.columns]
                        st.dataframe(
                            trades[cols_bt_ok].style.apply(_bt_style, axis=1),
                            use_container_width=True, height=320,
                        )

                        csv_bt = trades.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
                        st.download_button(
                            "⬇️ Exportar trades CSV", csv_bt,
                            file_name="backtest_trades.csv", mime="text/csv",
                        )

    # ── TAB 6: Plano Operacional + Risk Engine ─────────────────────────────
    with tab_exec:
        from src.quant.execution_assistant import ExecutionPlan, build_execution_plan
        from src.quant.risk_engine import RiskEngine, RiskConfig, RiskState

        st.markdown('<div class="sec-title">🎯 Plano Operacional — Execution Assistant</div>',
                    unsafe_allow_html=True)
        st.caption("⚠️ Apenas informativo — decisão e execução são exclusivamente do operador.")

        # Configuração do Risk Engine
        with st.expander("⚙️ Configurar Risk Engine", expanded=False):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                exec_capital   = st.number_input("Capital (R$)", 1_000, 500_000, 10_000, 1_000, key="exec_cap")
                exec_risk_pct  = st.slider("Risco/trade (%)", 0.1, 2.0, 0.5, 0.1, key="exec_rpct") / 100
            with ec2:
                exec_stop_pct  = st.slider("Stop (%)", 10, 60, 30, key="exec_stop") / 100
                exec_t1_pct    = st.slider("Alvo 1 (%)", 20, 100, 50, key="exec_t1") / 100
            with ec3:
                exec_t2_pct    = st.slider("Alvo 2 (%)", 50, 200, 100, key="exec_t2") / 100
                exec_daily_pnl = st.number_input("P&L diário atual (R$)", -5000.0, 5000.0, 0.0, 100.0, key="exec_dpnl")

        risk_cfg = RiskConfig(
            risk_pct_per_trade=exec_risk_pct,
            daily_loss_limit=0.02,
            weekly_loss_limit=0.04,
        )
        risk_state = RiskState(
            capital=exec_capital,
            daily_pnl=exec_daily_pnl,
        )
        risk_eng = RiskEngine(risk_cfg, risk_state)

        # Seletor de setup
        if not opps:
            st.warning("Nenhum setup disponível. Rode o scanner primeiro.")
        else:
            def _exec_label(i):
                o = opps[i]
                return f"{_STATUS_ICON.get(o.status,'')} {o.payoff.underlying} — {o.name} (Score {o.score:.0f})"

            exec_idx = st.selectbox("Setup para análise", range(len(opps)),
                                    format_func=_exec_label, key="exec_sel")
            opp_exec = opps[exec_idx]
            p_exec   = opp_exec.payoff

            main_leg_exec = next((l for l in p_exec.legs if l.option_type != "STOCK"), None)

            if main_leg_exec:
                entry_px = main_leg_exec.price
                stop_px  = round(entry_px * (1 - exec_stop_pct), 4)
                t1_px    = round(entry_px * (1 + exec_t1_pct), 4)
                t2_px    = round(entry_px * (1 + exec_t2_pct), 4)

                # Risk Engine evaluation
                contracts, risk_fin = risk_eng.compute_contracts(
                    entry_px, stop_px, contract_size=100, hist_vol=opp_exec.hv
                )
                verdict = risk_eng.evaluate(
                    underlying=p_exec.underlying,
                    option_type=main_leg_exec.option_type,
                    expiry=p_exec.expiry,
                    entry=entry_px,
                    stop=stop_px,
                    contracts=contracts,
                    hist_vol=opp_exec.hv,
                )

                # Cores do veredito
                verd_color = "#22C55E" if verdict.approved and not verdict.warnings \
                    else ("#F59E0B" if verdict.approved else "#EF4444")
                verd_icon  = "✅" if verdict.approved and not verdict.warnings \
                    else ("⚠️" if verdict.approved else "🚫")

                stop_pct_show  = round((1 - stop_px / entry_px) * 100, 1)
                t1_pct_show    = round((t1_px / entry_px - 1) * 100, 1)
                t2_pct_show    = round((t2_px / entry_px - 1) * 100, 1)
                rr_exec        = t1_pct_show / stop_pct_show if stop_pct_show > 0 else 0

                # Card do plano
                st.markdown(f"""
                    <div style="background:#0D1421;border:1px solid #1E3A5F;border-radius:12px;
                                padding:22px;margin-bottom:16px">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
                        <div>
                        <div style="font-size:1.4rem;font-weight:900;color:#F1F5F9">{p_exec.underlying}</div>
                        <div style="font-family:monospace;font-size:0.82rem;color:#334155">{main_leg_exec.ticker}</div>
                        </div>
                        <div style="text-align:right">
                        <div style="font-size:0.72rem;color:#334155">Risk Engine</div>
                        <div style="font-size:1rem;font-weight:900;color:{verd_color}">{verd_icon} {verdict.verdict_str}</div>
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px;margin-bottom:16px">
                        <div style="background:#111827;border:1px solid #1E2D42;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Entrada</div>
                        <div style="font-size:1.2rem;font-weight:800;color:#3B82F6">R${entry_px:.4f}</div>
                        </div>
                        <div style="background:#1c0909;border:1px solid #7f1d1d;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Stop</div>
                        <div style="font-size:1.2rem;font-weight:800;color:#EF4444">R${stop_px:.4f}</div>
                        <div style="font-size:0.65rem;color:#7f1d1d">−{stop_pct_show:.1f}%</div>
                        </div>
                        <div style="background:#052e16;border:1px solid #166534;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Alvo 1</div>
                        <div style="font-size:1.2rem;font-weight:800;color:#22C55E">R${t1_px:.4f}</div>
                        <div style="font-size:0.65rem;color:#166534">+{t1_pct_show:.1f}%</div>
                        </div>
                        <div style="background:#052e16;border:1px solid #166534;border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Alvo 2</div>
                        <div style="font-size:1.2rem;font-weight:800;color:#4ADE80">R${t2_px:.4f}</div>
                        <div style="font-size:0.65rem;color:#166534">+{t2_pct_show:.1f}%</div>
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:16px">
                        <div>
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase">Contratos sugeridos</div>
                        <div style="font-size:1rem;font-weight:800;color:#F1F5F9">{contracts}</div>
                        </div>
                        <div>
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase">Risco financeiro</div>
                        <div style="font-size:1rem;font-weight:800;color:#EF4444">R${risk_fin:,.0f}</div>
                        </div>
                        <div>
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase">R/R Alvo 1</div>
                        <div style="font-size:1rem;font-weight:800;color:#F1F5F9">{rr_exec:.1f}x</div>
                        </div>
                        <div>
                        <div style="font-size:0.6rem;color:#334155;text-transform:uppercase">P(Lucro)</div>
                        <div style="font-size:1rem;font-weight:800;color:#F1F5F9">{opp_exec.prob_profit:.1%}</div>
                        </div>
                    </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Alertas do Risk Engine
                if verdict.blocks:
                    for b in verdict.blocks:
                        st.error(f"🚫 {b}")
                if verdict.warnings:
                    for w in verdict.warnings:
                        st.warning(f"⚠️ {w}")

                # Payoff + Detalhes
                col_pf, col_dt = st.columns([3, 2])
                with col_pf:
                    _payoff_chart(opp_exec, st, height=380, show_metrics=True)
                with col_dt:
                    st.markdown(_detail_html(opp_exec), unsafe_allow_html=True)

                # Registrar no diário
                st.markdown('<div class="sec-title">💾 Registrar no Diário</div>', unsafe_allow_html=True)
                c_jrn1, c_jrn2 = st.columns(2)
                with c_jrn1:
                    jrn_contracts = st.number_input("Contratos (real)", 1, 1000,
                                                    max(contracts, 1), key="exec_jrn_c")
                    jrn_notes     = st.text_input("Observação", key="exec_jrn_notes")
                with c_jrn2:
                    jrn_entry_real = st.number_input("Entrada real (R$)", 0.001, 999.0,
                                                     entry_px, 0.001, key="exec_jrn_e",
                                                     format="%.4f")
                    jrn_stop_real  = st.number_input("Stop real (R$)", 0.001, 999.0,
                                                     stop_px, 0.001, key="exec_jrn_s",
                                                     format="%.4f")

                if st.button("💾 Salvar no diário", key="exec_save_jrn", type="primary"):
                    from src.journal.trade_journal import TradeJournal, JournalTrade
                    jrn_path = project_path(cfg["database_path"]).parent / "journal.db"
                    journal  = TradeJournal(jrn_path)
                    trade = JournalTrade(
                        underlying=p_exec.underlying,
                        ticker=main_leg_exec.ticker,
                        option_type=main_leg_exec.option_type,
                        direction="COMPRA" if main_leg_exec.direction == "BUY" else "VENDA",
                        strategy=p_exec.strategy_type,
                        entry_price=jrn_entry_real,
                        stop_price=jrn_stop_real,
                        target1=t1_px,
                        target2=t2_px,
                        contracts=jrn_contracts,
                        score=opp_exec.score,
                        notes=jrn_notes,
                    )
                    trade_id = journal.add_trade(trade)
                    st.success(f"✅ Trade #{trade_id} registrado no diário — {p_exec.underlying} · {main_leg_exec.ticker}")
            else:
                st.info("Estrutura sem opção identificável (stock-only). Selecione outra.")

    # ── TAB: Notícias ────────────────────────────────────────────────────────────
    with tab_news:
        try:
            from src.integration.news_bridge import (
                nh_db_available, get_news_for_asset, get_recent_alerts, get_all_recent
            )
            _nb_ok = True
        except Exception as _nb_err:
            _nb_ok = False
            def nh_db_available(): return False
            def get_news_for_asset(*a, **kw): return []
            def get_recent_alerts(*a, **kw): import pandas as _pd; return _pd.DataFrame()
            def get_all_recent(*a, **kw): import pandas as _pd; return _pd.DataFrame()
            st.warning(f"⚠️ News Bridge indisponível: {_nb_err}")

        st.markdown('<div class="sec-title">📰 Notícias — News Hunter</div>',
                    unsafe_allow_html=True)

        if not nh_db_available():
            st.warning(
                "Banco do News Hunter não encontrado. "
                "Certifique-se de que `12_PYTHON/news_hunter/banco.db` existe e "
                "rode `python main.py --coletar` no news_hunter para popular."
            )
        else:
            _score_badge = lambda s: (
                '<span style="background:#052e16;color:#22C55E;padding:1px 7px;'
                'border-radius:10px;font-size:0.68rem;font-weight:800">ALTO</span>'
                if (s or 0) >= 8 else
                '<span style="background:#1c1100;color:#F59E0B;padding:1px 7px;'
                'border-radius:10px;font-size:0.68rem;font-weight:800">MÉD</span>'
                if (s or 0) >= 5 else
                '<span style="background:#1A1A2E;color:#64748B;padding:1px 7px;'
                'border-radius:10px;font-size:0.68rem;font-weight:800">BAIXO</span>'
            )

            # ── Alertas urgentes ──
            alerts_df = get_recent_alerts(limit=10, days=3)
            if not alerts_df.empty:
                st.markdown('<div class="sec-title">🚨 Alertas Recentes (score alto / urgentes)</div>',
                            unsafe_allow_html=True)
                for _, row in alerts_df.iterrows():
                    score_html = _score_badge(row.get("score"))
                    st.markdown(f"""
                        <div style="background:#111827;border-left:3px solid #EF4444;
                                    border-radius:0 8px 8px 0;padding:10px 16px;margin-bottom:8px">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div style="font-size:0.82rem;font-weight:700;color:#E2E8F0">
                            {row.get('titulo','')}</div>
                            {score_html}
                        </div>
                        <div style="font-size:0.68rem;color:#334155;margin-top:4px">
                            {row.get('fonte','')} · {row.get('categoria','')} · {row.get('data_pub','')}
                        </div>
                        </div>
                        """, unsafe_allow_html=True)

            # ── Por ativo scaneado ──
            ativos_scan = sorted({o.payoff.underlying for o in opps})
            if ativos_scan:
                st.markdown('<div class="sec-title">🎯 Notícias por Ativo Scaneado</div>',
                            unsafe_allow_html=True)

                news_asset = st.selectbox("Ativo", ativos_scan, key="news_asset")
                n_days     = st.slider("Período (dias)", 1, 30, 7, key="news_days")

                asset_news = get_news_for_asset(news_asset, days=n_days, limit=8)
                if not asset_news:
                    st.info(f"Nenhuma notícia encontrada para {news_asset} nos últimos {n_days} dias.")
                else:
                    for n in asset_news:
                        score_html = _score_badge(n.get("score"))
                        resumo = n.get("resumo_ia") or n.get("resumo_curto") or ""
                        sentimento = n.get("sentimento") or "-"
                        tickers = n.get("tickers") or "-"
                        risco_opcoes = n.get("risco_opcoes") or "-"
                        score_vol = n.get("score_volatilidade") or "-"
                        st.markdown(f"""
                            <div style="font-size:0.72rem;color:#94A3B8;margin-top:8px;line-height:1.6">
                            🤖 <b>IA:</b> Sentimento: {sentimento} · Tickers: {tickers} · 
                            Risco Opções: {risco_opcoes} · Score Vol: {score_vol}
                            </div>
                            {"<div style='font-size:0.76rem;color:#64748B;margin-top:6px;line-height:1.5'>" + resumo + "</div>" if resumo else ""}
                            <div style="background:#111827;border:1px solid #1E2D42;
                                        border-radius:8px;padding:12px 16px;margin-bottom:8px">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
                                <div style="font-size:0.84rem;font-weight:700;color:#E2E8F0;flex:1">
                                {n.get('titulo','')}</div>
                                {score_html}
                            </div>
                            {"<div style='font-size:0.76rem;color:#64748B;margin-top:6px;line-height:1.5'>" + resumo + "</div>" if resumo else ""}
                            <div style="font-size:0.67rem;color:#334155;margin-top:6px">
                                {n.get('fonte','')} · {n.get('categoria','')} · {n.get('data_pub','')}
                            </div>
                            </div>
                            """, unsafe_allow_html=True)

            # ── Feed geral recente ──
            with st.expander("📋 Feed geral recente (todos os ativos)", expanded=False):
                all_news = get_all_recent(days=2, limit=40)
                if all_news.empty:
                    st.info("Sem notícias recentes no banco.")
                else:
                    for _, row in all_news.iterrows():
                        st.markdown(f"""
                            <div style="background:#0D1421;border-left:2px solid #1E3A5F;
                                        padding:8px 14px;margin-bottom:6px;border-radius:0 6px 6px 0">
                            <div style="font-size:0.8rem;color:#CBD5E1">{row.get('titulo','')}</div>
                            <div style="font-size:0.65rem;color:#334155;margin-top:3px">
                                {row.get('fonte','')} · {row.get('categoria','')} · {row.get('data_pub','')}
                            </div>
                            </div>
                            """, unsafe_allow_html=True)

            # ── Botão Telegram: enviar alerta de notícia urgente ──
            st.markdown("---")
            if st.button("📲 Enviar alertas urgentes via Telegram", key="tg_news_btn"):
                from src.notifications.telegram_bot import send_text, telegram_disponivel
                if not telegram_disponivel():
                    st.error("Telegram não configurado. Configure no news_hunter/config.py.")
                else:
                    alerts_df2 = get_recent_alerts(limit=5, days=1)
                    if alerts_df2.empty:
                        st.info("Sem alertas urgentes hoje.")
                    else:
                        lines = ["🚨 ALERTAS DE MERCADO — News Hunter\n"]
                        for _, row in alerts_df2.iterrows():
                            lines.append(f"• {row['titulo']}")
                            if row.get("fonte"):
                                lines.append(f"  {row['fonte']} · {row.get('data_pub','')}")
                            lines.append("")
                        lines.append("Fonte: News Hunter · Radar Quant")
                        ok = send_text("\n".join(lines))
                        (st.success if ok else st.error)(
                            "Alertas enviados!" if ok else "Falha no envio."
                        )

    # ── TAB 7: Ranking ──
    with tab_rank:
        st.subheader("Tabela de Ranking")

        if df.empty:
            st.warning("Nenhuma estrutura no ranking.")
        else:
            cols_show = [
                "rank", "status", "score", "underlying", "strategy",
                "risk_category", "cenario", "net_cost", "max_profit",
                "max_loss", "risk_reward", "prob_profit", "dte", "risk_level",
            ]
            cols_ok = [c for c in cols_show if c in df.columns]
            df_disp = df[cols_ok].copy()

            if "prob_profit" in df_disp.columns:
                df_disp["prob_profit"] = df_disp["prob_profit"].map("{:.1%}".format)
            if "risk_reward" in df_disp.columns:
                df_disp["risk_reward"] = df_disp["risk_reward"].apply(
                    lambda x: "∞" if math.isinf(x) else f"{x:.2f}x"
                )
            for col in ("net_cost", "max_profit", "max_loss"):
                if col in df_disp.columns:
                    df_disp[col] = df_disp[col].apply(
                        lambda v: "ilimitado"
                        if v is None or (isinstance(v, float) and math.isnan(v))
                        else f"R${v:,.0f}"
                    )

            _st_bg = {
                "OPERACIONAL": "#052e16", "ESTUDO": "#1c1100", "DESCARTAR": "#1c0909"
            }
            _rc_bg = {
                "BAIXO": "#052e16", "MODERADO": "#1c1100",
                "ALTO": "#1c0e00", "ALTO_RISCO_NAO_RECOMENDADO": "#1c0909",
            }

            def _style(row):
                out = [""] * len(row)
                idx_list = list(row.index)
                if "status" in row.index:
                    bg = _st_bg.get(row["status"], "")
                    out[idx_list.index("status")] = f"background:{bg};font-weight:700"
                if "risk_category" in row.index:
                    bg = _rc_bg.get(row.get("risk_category", ""), "")
                    out[idx_list.index("risk_category")] = f"background:{bg}"
                if "risk_level" in row.index and row.get("risk_level") == "ILIMITADO":
                    out[idx_list.index("risk_level")] = "background:#1c0909;color:#FCA5A5;font-weight:700"
                return out

            st.dataframe(
                df_disp.style.apply(_style, axis=1),
                use_container_width=True,
                height=480,
            )

            csv = df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
            st.download_button(
                "⬇️ Exportar CSV",
                csv,
                file_name="radar_quant_export.csv",
                mime="text/csv",
            )

    # ── TAB 8: Relatório ──
    with tab_report:
        st.subheader("Relatório Operacional")

        c1, c2 = st.columns(2)
        with c1:
            asset_fil = st.selectbox(
                "Ativo", ["Todos"] + sorted({o.payoff.underlying for o in opps})
            )
        with c2:
            status_fil = st.selectbox(
                "Status", ["Todos", "OPERACIONAL", "ESTUDO", "DESCARTAR"],
                key="rep_status",
            )

        filtered = [
            o for o in opps
            if (asset_fil  == "Todos" or o.payoff.underlying == asset_fil)
            and (status_fil == "Todos" or o.status == status_fil)
        ]

        if not filtered:
            st.info("Nenhuma estrutura com esses filtros.")
        else:
            from src.options.strategy_report import format_strategy_report
            for o in filtered[:10]:
                st.html(_compact_card(o))
                with st.expander("📊 Detalhes", expanded=False):
                    st.html(_detail_html(o))
                    _payoff_chart(o, st, height=320, show_metrics=False)


            report_txt = "\n\n".join(
                format_strategy_report(o, o.rank) for o in filtered[:10]
            )

            st.download_button(
                "⬇️ Baixar Relatório .txt",
                report_txt.encode("utf-8"),
                file_name=f"relatorio_{asset_fil}.txt",
                mime="text/plain",
            )


if __name__ == "__main__":
    main()
