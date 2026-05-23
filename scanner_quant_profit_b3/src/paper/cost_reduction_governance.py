"""Governanca para variantes simuladas de reducao de custos."""
from __future__ import annotations


def evaluate_cost_reduction_variant(row) -> str:
    """Classificar variante simulada antes de qualquer observacao recorrente."""
    get = row.get if hasattr(row, "get") else dict(row).get
    trades = int(get("trades_count", 0) or 0)
    base_trades = int(get("baseline_trades_count", trades) or trades or 0)
    cost_reduction = float(get("cost_reduction", 0) or 0)
    return_delta = float(get("return_delta", 0) or 0)
    drawdown_delta = float(get("drawdown_delta", 0) or 0)
    score = float(get("improvement_score", 0) or 0)
    if trades < 5 or (base_trades and trades < base_trades * 0.25):
        return "COST_REDUCTION_BLOCKED_LOW_SAMPLE"
    if cost_reduction <= 0:
        return "COST_REDUCTION_REJECTED"
    if return_delta < -0.005:
        return "COST_REDUCTION_BLOCKED_RETURN_DEGRADATION"
    if drawdown_delta < -0.02:
        return "COST_REDUCTION_BLOCKED_DRAWDOWN"
    if base_trades and trades < base_trades * 0.5:
        return "COST_REDUCTION_BLOCKED_OVERFITTING"
    if score >= 70 and return_delta >= -0.001 and drawdown_delta >= -0.005:
        return "COST_REDUCTION_APPROVED_FOR_MORE_TESTING"
    if score >= 55:
        return "COST_REDUCTION_OBSERVATION_ONLY"
    return "COST_REDUCTION_REJECTED"
