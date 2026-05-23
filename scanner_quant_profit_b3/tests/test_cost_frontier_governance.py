from src.paper.cost_frontier_governance import evaluate_cost_frontier_candidate


def test_evaluate_cost_frontier_candidate_requires_efficiency():
    row = {"is_efficient": False, "trades_count": 10, "return_delta": 0, "drawdown_delta": 0, "turnover_delta": -1, "tradeoff_score": 80}

    assert evaluate_cost_frontier_candidate(row) == "COST_FRONTIER_REJECTED"


def test_evaluate_cost_frontier_candidate_blocks_drawdown():
    row = {"is_efficient": True, "trades_count": 10, "return_delta": 0.01, "drawdown_delta": -0.03, "turnover_delta": -1, "tradeoff_score": 80}

    assert evaluate_cost_frontier_candidate(row) == "COST_FRONTIER_BLOCKED_DRAWDOWN"
