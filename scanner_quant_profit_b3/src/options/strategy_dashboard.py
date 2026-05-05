"""
Radar Quant — Interface Profissional de Trading de Opções B3
Dark mode · Cards · Nível XP / BTG / TradingView
"""
from __future__ import annotations

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

/* SCROLLBAR */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D42; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2D4A6B; }
</style>
"""

# ── JS: relógio ao vivo ─────────────────────────────────────────────────────

_CLOCK_JS = """
<script>
(function() {
  function tick() {
    var el = document.getElementById('rq-clock-val');
    if (el) {
      var n = new Date();
      el.textContent = n.toLocaleTimeString('pt-BR', {
        hour:'2-digit', minute:'2-digit', second:'2-digit'
      });
    }
    setTimeout(tick, 1000);
  }
  tick();
})();
</script>
"""

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
        "contexto":   contexto,
        "leitura":    leitura,
        "estrategia": estrategia,
        "por_que":    por_que,
        "cenario":    p.best_scenario,
        "risco":      risco,
    }


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
  </div>

  <div class="tt-divider"></div>

  <div class="tt-row">
    <span class="tt-key">1. Vale operar?</span>
    <span class="tt-val tt-val-g">{_STATUS_ICON.get(opp.status,'')} Sim</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">2. Ativo</span>
    <span class="tt-val">{p.underlying}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">3. Opção</span>
    <span class="tt-val" style="font-family:monospace">{opcao_str}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">4. Direção</span>
    <span class="tt-val">{dir_text}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">5. Risco máx</span>
    <span class="tt-val {loss_cls}">{loss_txt}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">6. Alvo (ganho)</span>
    <span class="tt-val {profit_cls}">{profit_txt}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">P(Lucro)</span>
    <span class="tt-val">{opp.prob_profit:.0%}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">R/R</span>
    <span class="tt-val">{rr_txt}</span>
  </div>
  <div class="tt-row">
    <span class="tt-key">DTE</span>
    <span class="tt-val">{p.dte}d · {p.expiry}</span>
  </div>

  <div class="tt-bar-bg">
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
      <span style="font-size:0.7rem;font-weight:700;background:{cat_bg};color:{cat_fg};padding:2px 8px;border-radius:10px">{cat_short}</span>
      <span style="font-size:0.72rem;color:#334155">
        DTE {p.dte}d &nbsp;·&nbsp; {p.expiry} &nbsp;·&nbsp;
        {opp.market_condition.value} &nbsp;·&nbsp; Aderência {opp.scenario_adherence:.0%}
      </span>
    </div>
    <div class="sc-prog">
      <div style="width:{sc_w}%;height:3px;border-radius:3px;background:{sc_color}"></div>
    </div>
  </div>

  <div class="sc-body" style="border-bottom:1px solid #162034">
    <div class="human-text">{report['contexto']}</div>
    <div style="font-size:0.76rem;color:#334155;margin-top:4px">{report['leitura']}</div>
  </div>

  <div class="sc-body">
    <div class="sc-grid">
      <div>
        <div class="sc-col-head">📊 Dados</div>
        <div class="sc-row"><span class="sc-dk">Custo</span><span class="sc-dv">{cost_txt}</span></div>
        <div class="sc-row"><span class="sc-dk">Ganho máx</span><span class="sc-dv sc-dv-g">{profit_txt}</span></div>
        <div class="sc-row"><span class="sc-dk">Perda máx</span><span class="sc-dv sc-dv-r">{loss_txt}</span></div>
        <div class="sc-row"><span class="sc-dk">R/R</span><span class="sc-dv">{rr_txt}</span></div>
      </div>
      <div>
        <div class="sc-col-head">💰 Risco</div>
        <div class="sc-row"><span class="sc-dk">Categoria</span><span style="font-size:0.72rem;font-weight:700;background:{cat_bg};color:{cat_fg};padding:1px 7px;border-radius:10px">{p.risk_category}</span></div>
        <div class="sc-row"><span class="sc-dk">P(Lucro)</span><span class="sc-dv">{opp.prob_profit:.1%}</span></div>
        <div class="sc-row"><span class="sc-dk">HV usada</span><span class="sc-dv">{opp.hv:.1%}</span></div>
        <div class="sc-row"><span class="sc-dk">Breakeven</span><span class="sc-dv">{be_txt}</span></div>
      </div>
      <div>
        <div class="sc-col-head">🎯 Operacional</div>
        <div style="font-size:0.78rem;color:#94A3B8;margin-bottom:8px">
          <span class="sc-col-head">Entrada</span>
          <div style="color:#64748B">{p.entry_condition}</div>
        </div>
        <div style="font-size:0.78rem;color:#94A3B8">
          <span class="sc-col-head">Saída</span>
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

def _payoff_chart(opp, st):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        st.warning("matplotlib não instalado")
        return

    p = opp.payoff
    S, pps = p.payoff_array(300)

    bg = "#080D17"
    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor(bg)
    ax.set_facecolor("#111827")

    ax.plot(S, pps, color="#3B82F6", linewidth=2.2, label=p.name)
    ax.axhline(0, color="#334155", linewidth=0.8, linestyle="--")
    ax.axvline(p.stock_price, color="#F59E0B", linewidth=1.4,
               linestyle=":", label=f"Spot R${p.stock_price:.2f}")
    for be in p.breakevens:
        ax.axvline(be, color="#EF4444", linewidth=1.1, linestyle="--",
                   label=f"BE R${be:.2f}")
    ax.fill_between(S, pps, 0, where=(pps > 0), alpha=0.12, color="#22C55E")
    ax.fill_between(S, pps, 0, where=(pps < 0), alpha=0.12, color="#EF4444")

    ax.set_xlabel("Preço no vencimento (R$)", fontsize=9, color="#475569")
    ax.set_ylabel("Resultado por ação (R$)", fontsize=9, color="#475569")
    ax.set_title(
        f"Payoff — {p.name} ({p.underlying})  |  DTE {p.dte}d  |  Vto {p.expiry}",
        fontsize=10, fontweight="bold", color="#94A3B8",
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:.2f}"))
    ax.tick_params(colors="#334155")
    for spine in ax.spines.values():
        spine.set_color("#1E2D42")
    ax.legend(fontsize=8, facecolor="#111827", edgecolor="#1E2D42",
              labelcolor="#64748B")
    ax.grid(True, alpha=0.1, color="#1E2D42")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo",     f"R${abs(p.net_cost):,.0f}",
              "débito" if p.net_cost > 0 else "crédito")
    c2.metric("Ganho máx", f"R${p.max_profit:,.0f}" if not math.isinf(p.max_profit) else "Ilimitado")
    c3.metric("Perda máx", f"R${p.max_loss:,.0f}"   if not math.isinf(p.max_loss)   else "Ilimitado")
    c4.metric("P(Lucro)",  f"{opp.prob_profit:.1%}")


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
        st.markdown("### 🎛 Radar Quant")
        st.markdown("---")

        cfg  = load_config()
        qcfg = load_quant_config()
        ativos_cfg = qcfg.get("ativos_permitidos", ["PETR4"])

        st.markdown("**Escopo**")
        modo_scan = st.radio(
            "Escopo", ["Todos os ativos", "Ativo específico"],
            label_visibility="collapsed",
        )
        selected_asset = (
            st.selectbox("Ativo", ativos_cfg)
            if modo_scan == "Ativo específico" else None
        )

        top_n = st.slider("Máx. estruturas", 5, 60, 20)

        st.markdown("---")
        st.markdown("**Modo**")
        modo = st.radio(
            "Modo operacional",
            ["🛡 Conservador", "⚡ Agressivo"],
            label_visibility="collapsed",
        )
        scan_mode = "conservative" if "Conservador" in modo else "normal"

        st.markdown("---")
        st.markdown("**Filtros**")

        filter_status = st.multiselect(
            "Status",
            ["OPERACIONAL", "ESTUDO", "DESCARTAR"],
            default=["OPERACIONAL", "ESTUDO"],
        )
        filter_types = st.multiselect(
            "Tipo de estratégia",
            ["SPREAD_ALTA", "SPREAD_BAIXA", "CONDOR", "BUTTERFLY",
             "VOLATILIDADE", "RENDA", "PROTECAO", "DIRECIONAL"],
        )

        tipo_opcao = st.multiselect(
            "Tipo de opção",
            ["CALL", "PUT"],
        )

        score_min = st.slider("Score mínimo", 0, 80, 30)
        dte_range = st.slider("DTE (dias)", 5, 90, (10, 60))

        only_definido = st.checkbox("Apenas risco definido", value=True)
        no_margin     = st.checkbox("Excluir com margem",    value=False)

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

    # ── HEADER ──
    st.markdown(f"""
    {_CLOCK_JS}
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
    """, unsafe_allow_html=True)

    # ── KPI STRIP ──
    st.markdown(f"""
    <div class="kpi-strip">
      <div class="kpi-card kc-blue">
        <div class="kpi-label">Estruturas</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-sub">{n_ativos} ativo{"s" if n_ativos != 1 else ""}</div>
      </div>
      <div class="kpi-card kc-green">
        <div class="kpi-label">✅ Operacional</div>
        <div class="kpi-value" style="color:#22C55E">{n_op}</div>
        <div class="kpi-sub">pronto para operar</div>
      </div>
      <div class="kpi-card kc-amber">
        <div class="kpi-label">📋 Estudo</div>
        <div class="kpi-value" style="color:#F59E0B">{n_est}</div>
        <div class="kpi-sub">monitorar</div>
      </div>
      <div class="kpi-card kc-purple">
        <div class="kpi-label">Score Médio</div>
        <div class="kpi-value">{avg_sc:.0f}</div>
        <div class="kpi-sub">de 100</div>
      </div>
      <div class="kpi-card kc-slate">
        <div class="kpi-label">P(Lucro) Médio</div>
        <div class="kpi-value">{avg_pp:.0%}</div>
        <div class="kpi-sub">modelo lognormal</div>
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

        cols = st.columns(len(top_opps))
        for i, (col, opp) in enumerate(zip(cols, top_opps)):
            with col:
                st.markdown(_top_trade_card(opp, i + 1), unsafe_allow_html=True)
                if st.button(
                    "▶ Ver Detalhe",
                    key=f"tt_btn_{i}",
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
                st.markdown(_setup_card(sel), unsafe_allow_html=True)
            with c_right:
                _payoff_chart(sel, st)
                st.markdown(_detail_html(sel), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TABS
    # ═══════════════════════════════════════════════════════════════════════
    tab_opp, tab_chart, tab_payoff, tab_flow_ml, tab_backtest, tab_rank, tab_report = st.tabs([
        "📋 Todos os Setups", "📊 Gráfico", "📈 Payoff",
        "🤖 Fluxo & ML", "⚙️ Backtest", "📊 Ranking", "📄 Relatório",
    ])

    # ── TAB 1: Todos os Setups ──
    with tab_opp:
        groups = [
            ("✅ Operacional — prontos para operar", "OPERACIONAL"),
            ("📋 Em Estudo — monitorar",             "ESTUDO"),
            ("❌ Descartar — evitar",                "DESCARTAR"),
        ]

        any_shown = False
        for group_title, status_key in groups:
            group_opps = [o for o in opps if o.status == status_key]
            if not group_opps:
                continue
            any_shown = True
            st.markdown(
                f'<div class="sec-title">{group_title} ({len(group_opps)})</div>',
                unsafe_allow_html=True,
            )
            for opp in group_opps:
                st.markdown(_setup_card(opp), unsafe_allow_html=True)
                with st.expander(
                    f"📈 Payoff + Detalhe · {opp.payoff.underlying} — {opp.name}",
                    expanded=False,
                ):
                    c_left, c_right = st.columns([2, 1])
                    with c_left:
                        _payoff_chart(opp, st)
                    with c_right:
                        st.markdown(_detail_html(opp), unsafe_allow_html=True)

        if not any_shown:
            st.info("Nenhuma oportunidade com os filtros atuais.")

    # ── TAB 2: Gráfico profissional ──────────────────────────────────────────
    with tab_chart:
        from src.options.chart_engine import render_chart, load_ohlcv, HAS_PLOTLY

        if not HAS_PLOTLY:
            st.warning("Instale plotly: `pip install plotly`")
        else:
            ativos_disponiveis = sorted({o.payoff.underlying for o in opps})
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                chart_asset = st.selectbox(
                    "Ativo", ativos_disponiveis,
                    key="chart_asset",
                )
            with c2:
                chart_days = st.select_slider(
                    "Período", [60, 120, 252, 504], value=252,
                    key="chart_days",
                )
            with c3:
                sync_setup = st.checkbox("Sincronizar setup", value=True, key="chart_sync")

            # Setup sincronizado com o ativo selecionado
            setup_for_chart = None
            if sync_setup:
                matching = [o for o in opps if o.payoff.underlying == chart_asset]
                if matching:
                    setup_for_chart = max(matching, key=lambda o: o.score)

            db_path = project_path(cfg["database_path"])
            con_chart = sqlite3.connect(db_path)
            try:
                fig = render_chart(chart_asset, con_chart, setup_for_chart, chart_days)
            finally:
                con_chart.close()

            if fig is None:
                st.info(f"Sem dados OHLCV para {chart_asset} no banco.")
            else:
                st.plotly_chart(fig, use_container_width=True)

            # Setup sincronizado — exibe o card abaixo do gráfico
            if sync_setup and setup_for_chart:
                st.markdown(
                    f'<div class="sec-title">Setup sincronizado — {setup_for_chart.payoff.underlying} · {setup_for_chart.name}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(_setup_card(setup_for_chart), unsafe_allow_html=True)

    # ── TAB 3: Payoff interativo ──
    with tab_payoff:
        st.subheader("Gráfico de Payoff no Vencimento")

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

        _payoff_chart(opp_sel, st)
        st.markdown(_detail_html(opp_sel), unsafe_allow_html=True)

    # ── TAB 4: Fluxo & ML ────────────────────────────────────────────────────
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
                st.markdown(_setup_card(opp), unsafe_allow_html=True)
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
            report_txt = "\n\n".join(
                format_strategy_report(o, o.rank) for o in filtered[:10]
            )
            st.code(report_txt, language=None)
            st.download_button(
                "⬇️ Baixar Relatório .txt",
                report_txt.encode("utf-8"),
                file_name=f"relatorio_{asset_fil}.txt",
                mime="text/plain",
            )


if __name__ == "__main__":
    main()
