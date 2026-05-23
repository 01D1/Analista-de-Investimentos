from src.paper.cost_tradeoff_score import calculate_cost_tradeoff_score


def test_calculate_cost_tradeoff_score_blocks_critical_governance():
    result = calculate_cost_tradeoff_score({"cost_reduction_pct": 0.8, "return_delta": 0.1, "drawdown_delta": 0.1, "turnover_delta": -1, "trades_count": 10, "governance_status": "COST_REDUCTION_BLOCKED_DRAWDOWN"})

    assert result["tradeoff_class"] == "TRADEOFF_BLOCKED"
    assert result["tradeoff_score"] < 100
