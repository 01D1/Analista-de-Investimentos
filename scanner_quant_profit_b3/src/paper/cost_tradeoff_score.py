"""Score de trade-off custo-retorno-drawdown."""
from __future__ import annotations


CRITICAL_BLOCKS = {
    "COST_REDUCTION_BLOCKED_DRAWDOWN",
    "COST_REDUCTION_BLOCKED_RETURN_DEGRADATION",
    "COST_REDUCTION_BLOCKED_LOW_SAMPLE",
}


def calculate_cost_tradeoff_score(row) -> dict:
    """Calcular score 0-100 e classe de trade-off."""
    get = row.get if hasattr(row, "get") else dict(row).get
    cost = max(min(float(get("cost_reduction_pct", 0) or 0), 1.0), -1.0)
    ret = float(get("return_delta", 0) or 0)
    dd = float(get("drawdown_delta", 0) or 0)
    turnover = float(get("turnover_delta", 0) or 0)
    trades = float(get("trades_count", 0) or 0)
    gov = str(get("governance_status", ""))
    cost_reduction_score = max(0.0, min(100.0, cost * 100))
    return_preservation_score = max(0.0, min(100.0, 100 + (ret / 0.01) * 50))
    drawdown_control_score = max(0.0, min(100.0, 100 + (dd / 0.02) * 50))
    turnover_control_score = 70.0 if turnover <= 0 else max(0.0, 70.0 - min(turnover / 100000, 70.0))
    sample_preservation_score = 100.0 if trades >= 10 else 50.0 if trades >= 5 else 0.0
    governance_penalty = 35.0 if gov in CRITICAL_BLOCKS else 15.0 if "REJECTED" in gov or "BLOCKED" in gov else 0.0
    score = (
        0.25 * cost_reduction_score
        + 0.25 * return_preservation_score
        + 0.25 * drawdown_control_score
        + 0.10 * turnover_control_score
        + 0.15 * sample_preservation_score
        - governance_penalty
    )
    score = round(max(0.0, min(100.0, score)), 6)
    if governance_penalty >= 35:
        klass = "TRADEOFF_BLOCKED"
    elif score >= 75:
        klass = "TRADEOFF_STRONG"
    elif score >= 60:
        klass = "TRADEOFF_PROMISING"
    elif score >= 40:
        klass = "TRADEOFF_WEAK"
    else:
        klass = "TRADEOFF_BAD"
    return {
        "cost_reduction_score": round(cost_reduction_score, 6),
        "return_preservation_score": round(return_preservation_score, 6),
        "drawdown_control_score": round(drawdown_control_score, 6),
        "turnover_control_score": round(turnover_control_score, 6),
        "sample_preservation_score": round(sample_preservation_score, 6),
        "governance_penalty": round(governance_penalty, 6),
        "tradeoff_score": score,
        "tradeoff_class": klass,
    }
