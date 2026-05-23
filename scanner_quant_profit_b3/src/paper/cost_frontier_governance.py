"""Governança da fronteira custo-retorno-drawdown."""
from __future__ import annotations


def evaluate_cost_frontier_candidate(row) -> str:
    get = row.get if hasattr(row, "get") else dict(row).get
    efficient = bool(get("is_efficient", False))
    trades = int(get("trades_count", 0) or 0)
    ret = float(get("return_delta", 0) or 0)
    dd = float(get("drawdown_delta", 0) or 0)
    turnover = float(get("turnover_delta", 0) or 0)
    score = float(get("tradeoff_score", 0) or 0)
    previous = str(get("governance_status", ""))
    if trades < 5:
        return "COST_FRONTIER_BLOCKED_LOW_SAMPLE"
    if not efficient:
        return "COST_FRONTIER_REJECTED"
    if "LOW_SAMPLE" in previous:
        return "COST_FRONTIER_BLOCKED_LOW_SAMPLE"
    if ret < -0.005 or "RETURN_DEGRADATION" in previous:
        return "COST_FRONTIER_BLOCKED_RETURN_LOSS"
    if dd < -0.02 or "DRAWDOWN" in previous:
        return "COST_FRONTIER_BLOCKED_DRAWDOWN"
    if turnover > 500000:
        return "COST_FRONTIER_BLOCKED_TURNOVER"
    if score >= 70:
        return "COST_FRONTIER_APPROVED_FOR_MORE_TESTING"
    if score >= 55:
        return "COST_FRONTIER_OBSERVATION_ONLY"
    return "COST_FRONTIER_REJECTED"
