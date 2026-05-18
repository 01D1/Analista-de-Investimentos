"""Governanca multi-cenario do paper trading."""
from __future__ import annotations


def evaluate_multi_scenario_governance(summary: dict) -> dict:
    positive = float(summary.get("positive_periods_pct", 0) or 0)
    mean_return = float(summary.get("mean_return", 0) or 0)
    drawdown = abs(float(summary.get("mean_drawdown", 0) or 0))
    periods = int(summary.get("periods_count", 0) or 0)
    scenarios = int(summary.get("scenarios_count", 0) or 0)
    sources = int(summary.get("signal_sources_count", 0) or 0)
    cost_class = str(summary.get("cost_robustness_class", "")).upper()
    regime_fragile = bool(summary.get("regime_fragile", False))
    robustness = str(summary.get("robustness", "")).upper()
    reasons_for = []
    reasons_against = []
    if periods < 2 or scenarios < 3:
        status = "PAPER_SCENARIO_BLOCKED_LOW_SAMPLE"
        reasons_against.append("Amostra multi-periodo ou multi-cenario insuficiente.")
    elif "OVERFIT" in robustness:
        status = "PAPER_SCENARIO_BLOCKED_OVERFITTING"
        reasons_against.append("Resultado concentrado sugere overfitting.")
    elif "FRAGILE" in cost_class:
        status = "PAPER_SCENARIO_BLOCKED_COST_SENSITIVE"
        reasons_against.append("Regra simulada perde robustez em cenario de custo.")
    elif regime_fragile:
        status = "PAPER_SCENARIO_BLOCKED_REGIME_FRAGILE"
        reasons_against.append("Resultado depende de poucos regimes de mercado.")
    elif mean_return < 0:
        status = "PAPER_SCENARIO_BLOCKED_NEGATIVE_RETURN"
        reasons_against.append("Retorno medio multi-cenario negativo.")
    elif positive >= 0.60 and mean_return > 0 and drawdown <= 0.15 and sources >= 2:
        status = "PAPER_SCENARIO_ROBUST_FOR_STUDY"
        reasons_for.append("Resultado positivo em multiplos periodos, cenarios e fontes de sinal.")
    elif positive >= 0.50 and mean_return > 0:
        status = "PAPER_SCENARIO_PROMISING"
        reasons_for.append("Resultado promissor, mas ainda requer observacao fora da amostra.")
    else:
        status = "PAPER_SCENARIO_OBSERVATION_ONLY"
        reasons_against.append("Robustez insuficiente para aprovacao analitica.")
    return {
        "governance_status": status,
        "approved_for_study": status == "PAPER_SCENARIO_ROBUST_FOR_STUDY",
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": ["Manter regra simulada como parametro em estudo e ampliar janelas/fontes antes de qualquer uso."],
    }
