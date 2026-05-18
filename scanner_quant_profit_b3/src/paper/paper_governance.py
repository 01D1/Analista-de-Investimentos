"""Governança de simulação/paper trading."""
from __future__ import annotations


def evaluate_paper_simulation(summary: dict) -> dict:
    trades = int(summary.get("trades_count", summary.get("turnover", 0)) or 0)
    total_return = float(summary.get("total_return", 0) or 0)
    max_drawdown = abs(float(summary.get("max_drawdown", 0) or 0))
    turnover = float(summary.get("turnover", trades) or 0)
    exit_events = int(summary.get("exit_events_count", 0) or 0)
    rebalance_events = int(summary.get("rebalance_events_count", 0) or 0)
    advanced = bool(summary.get("advanced_rules", False))
    reasons_for = []
    reasons_against = []
    status = "PAPER_OBSERVATION_ONLY"
    if advanced and trades < 10:
        status = "PAPER_REQUIRES_MORE_DATA"
        reasons_against.append("Regras avançadas precisam de mais amostra simulada.")
    elif trades < 5:
        status = "PAPER_BLOCKED_LOW_SAMPLE"
        reasons_against.append("Amostra insuficiente de ordens simuladas.")
    elif max_drawdown > 0.20:
        status = "PAPER_BLOCKED_DRAWDOWN"
        reasons_against.append("Drawdown simulado acima do limite.")
    elif advanced and exit_events > max(trades * 2, 20):
        status = "PAPER_BLOCKED_OVERTRADING"
        reasons_against.append("Regras avançadas geraram excesso de saídas simuladas.")
    elif advanced and rebalance_events > max(trades * 2, 20):
        status = "PAPER_BLOCKED_RULE_OVERFIT"
        reasons_against.append("Rebalanceamento simulado possivelmente excessivo.")
    elif total_return < 0:
        status = "PAPER_ADVANCED_RULES_NO_IMPROVEMENT" if advanced else "PAPER_BLOCKED_NEGATIVE_RETURN"
        reasons_against.append("Retorno simulado negativo ou sem melhora com regras avançadas.")
    elif turnover > 250:
        status = "PAPER_BLOCKED_HIGH_TURNOVER"
        reasons_against.append("Turnover simulado excessivo.")
    else:
        status = "PAPER_ADVANCED_RULES_IMPROVED" if advanced else "PAPER_APPROVED_FOR_REVIEW"
        reasons_for.append("Simulação com retorno e risco dentro dos critérios de revisão.")
    return {"governance_status": status, "reasons_for": reasons_for, "reasons_against": reasons_against, "required_actions": ["Revisar resultados fora da amostra antes de qualquer uso operacional."]}
