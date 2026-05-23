from src.paper.limit_signal_source_governance import evaluate_limit_signal_source_variant


def test_limit_signal_source_governance_approves_observation():
    status = evaluate_limit_signal_source_variant({"positive_improvement_pct": 0.7, "mean_return_delta": 0.001, "mean_drawdown_delta": 0, "mean_fragility_delta": -2, "mean_cost_drag_delta": -1, "mean_slippage_delta": -1, "trades_count": 50, "removed_pct": 0.2})
    assert status == "LIMIT_SOURCE_APPROVED_FOR_OBSERVATION"


def test_limit_signal_source_governance_blocks_cost():
    assert evaluate_limit_signal_source_variant({"trades_count": 50, "mean_cost_drag_delta": 1}) == "LIMIT_SOURCE_BLOCKED_COST"

