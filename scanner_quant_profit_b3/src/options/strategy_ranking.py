"""
Strategy Ranking

Calcula o score final de cada oportunidade e ordena o ranking.

Componentes do score (soma = 100):
  liquidez_legs    25 — liquidez mínima das pernas
  risco_retorno    20 — relação max_profit / max_loss
  prob_lucro       20 — probabilidade lognormal de lucro
  aderencia        15 — quão bem se encaixa no cenário
  dte              10 — DTE no range ideal (15-45 dias)
  risco_definido   10 — bônus se risco máximo é definido
"""
from __future__ import annotations

import math
from typing import List

from src.options.strategy_builder import StrategyOpportunity
from src.options.payoff_models import CONTRACT_SIZE

# Range ideal de DTE para a maioria das estratégias
DTE_IDEAL_MIN = 15
DTE_IDEAL_MAX = 45

# Multiplicador de score por categoria de risco
_RISK_MULTIPLIER = {
    "BAIXO": 1.15,
    "MODERADO": 1.00,
    "ALTO": 0.75,
    "ALTO_RISCO_NAO_RECOMENDADO": 0.30,
}


def score_strategy(opp: StrategyOpportunity) -> float:
    """Calcula score 0-100 para uma StrategyOpportunity."""
    p = opp.payoff

    # --- Liquidez das pernas ---
    scores_liq = [
        l.liq_score for l in opp.legs
        if hasattr(l, "liq_score") and l.option_type != "STOCK"
    ]
    liq = (sum(scores_liq) / len(scores_liq)) if scores_liq else 0.0
    s_liq = (liq / 100.0) * 25.0

    # --- Relação risco/retorno ---
    if not math.isinf(p.max_loss) and p.max_loss > 0 and not math.isinf(p.max_profit):
        rr = min(p.max_profit / p.max_loss, 5.0)  # cap em 5x
        s_rr = (rr / 5.0) * 20.0
    elif math.isinf(p.max_profit):
        s_rr = 14.0  # potencial ilimitado mas penaliza levemente
    else:
        s_rr = 0.0

    # --- Probabilidade de lucro ---
    s_prob = opp.prob_profit * 20.0

    # --- Aderência ao cenário ---
    s_adh = opp.scenario_adherence * 15.0

    # --- DTE ---
    dte = p.dte
    if DTE_IDEAL_MIN <= dte <= DTE_IDEAL_MAX:
        s_dte = 10.0
    elif dte < DTE_IDEAL_MIN:
        s_dte = max(0.0, (dte / DTE_IDEAL_MIN) * 10.0)
    else:
        over = dte - DTE_IDEAL_MAX
        s_dte = max(0.0, 10.0 - (over / 15.0) * 10.0)

    # --- Risco definido ---
    s_risk = 10.0 if p.risk_level == "DEFINIDO" else 0.0

    total = s_liq + s_rr + s_prob + s_adh + s_dte + s_risk
    mult = _RISK_MULTIPLIER.get(p.risk_category, 1.0)
    return round(min(total * mult, 100.0), 2)


def rank_strategies(
    opportunities: List[StrategyOpportunity],
    top: int = 20,
) -> List[StrategyOpportunity]:
    """
    Atribui scores, ordena e numera o ranking.
    Retorna top N oportunidades.
    """
    for opp in opportunities:
        opp.score = score_strategy(opp)

    ranked = sorted(opportunities, key=lambda o: o.score, reverse=True)
    for i, opp in enumerate(ranked, start=1):
        opp.rank = i

    return ranked[:top]


def rank_summary(opportunities: List[StrategyOpportunity]) -> str:
    """Tabela resumida do ranking para o terminal."""
    if not opportunities:
        return "Nenhuma estrutura encontrada."

    lines = [
        f"{'#':>3}  {'Estratégia':<32}  {'Ativo':<8}  "
        f"{'Score':>6}  {'P(Lucro)':>8}  {'R/R':>5}  "
        f"{'Custo':>8}  {'DTE':>4}  Cenário"
    ]
    lines.append("─" * 110)
    for opp in opportunities:
        p = opp.payoff
        rr = f"{p.risk_reward:.1f}x" if not math.isinf(p.risk_reward) else "∞"
        cost = f"R${p.net_cost:+.0f}"
        lines.append(
            f"{opp.rank:>3}  {opp.name:<32}  {opp.underlying:<8}  "
            f"{opp.score:>6.1f}  {opp.prob_profit:>7.1%}  {rr:>5}  "
            f"{cost:>8}  {p.dte:>4}d  {opp.market_condition.value}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Ranking institucional leve para a Fase 19
# ---------------------------------------------------------------------------

def _clip_score(value: float) -> float:
    if value != value:
        return 0.0
    return round(max(0.0, min(100.0, float(value))), 4)


def score_option_structure(structure: dict, context: dict | None = None) -> dict:
    context = context or {}
    max_profit = structure.get("max_profit", 0)
    max_loss = structure.get("max_loss", 0)
    ratio = structure.get("payoff_ratio", 0) or 0
    liquidity = float(structure.get("liquidity_score") or 0)
    risk = float(structure.get("risk_score") or 0)
    dte = float(context.get("days_to_maturity") or 30)
    spread = float(context.get("spread_pct") or 0)
    payoff_score = 70 if math.isinf(max_profit) else _clip_score(min(float(ratio), 3) / 3 * 100)
    liquidity_score = liquidity
    risk_score = risk if max_loss and not math.isinf(max_loss) else 20
    cost_score = _clip_score(100 - min(spread, 50) * 2)
    time_decay_score = _clip_score(100 - max(0, 15 - dte) * 4)
    moneyness_score = float(context.get("moneyness_score") or 60)
    volatility_score = float(context.get("volatility_score") or 50)
    regime_score = float(context.get("regime_score") or 50)
    event_context_score = float(context.get("event_context_score") or 50)
    score_final = _clip_score(
        payoff_score * 0.22
        + liquidity_score * 0.22
        + risk_score * 0.18
        + cost_score * 0.12
        + time_decay_score * 0.10
        + moneyness_score * 0.06
        + volatility_score * 0.04
        + regime_score * 0.03
        + event_context_score * 0.03
    )
    row = {
        **structure,
        "payoff_score": round(payoff_score, 4),
        "cost_score": round(cost_score, 4),
        "time_decay_score": round(time_decay_score, 4),
        "moneyness_score": round(moneyness_score, 4),
        "volatility_score": round(volatility_score, 4),
        "regime_score": round(regime_score, 4),
        "event_context_score": round(event_context_score, 4),
        "structure_score": score_final,
    }
    row["candidate_status"] = classify_option_strategy_candidate(row)
    row["explanation"] = explain_option_structure_score(row)
    return row


def classify_option_strategy_candidate(score_row: dict) -> str:
    if not score_row:
        return "DADOS_INSUFICIENTES"
    if float(score_row.get("liquidity_score") or 0) < 30:
        return "LIQUIDEZ_INSUFICIENTE"
    if float(score_row.get("risk_score") or 0) < 25:
        return "RISCO_ELEVADO"
    score = float(score_row.get("structure_score") or 0)
    if score >= 75:
        return "ESTRUTURA_INTERESSANTE"
    if score >= 60:
        return "ASSIMETRIA_A_INVESTIGAR"
    if score >= 45:
        return "APENAS_OBSERVAR"
    return "DESCARTAR"


def explain_option_structure_score(score_row: dict) -> str:
    status = score_row.get("candidate_status", "DADOS_INSUFICIENTES")
    notes = []
    if float(score_row.get("liquidity_score") or 0) < 30:
        notes.append("liquidez insuficiente")
    if float(score_row.get("risk_score") or 0) < 35:
        notes.append("risco elevado")
    if float(score_row.get("time_decay_score") or 0) < 50:
        notes.append("theta/vencimento exigem cautela")
    if not notes:
        notes.append("payoff/risco e liquidez em patamar aceitável para estudo")
    return f"{status}: estrutura potencial a estudar com {', '.join(notes)}. Não é recomendação operacional."
