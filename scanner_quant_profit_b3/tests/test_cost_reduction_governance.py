from src.paper.cost_reduction_governance import evaluate_cost_reduction_variant


def test_evaluate_cost_reduction_variant_approves_more_testing():
    row = {"trades_count": 20, "baseline_trades_count": 20, "cost_reduction": 100, "return_delta": 0, "drawdown_delta": 0, "improvement_score": 75}

    assert evaluate_cost_reduction_variant(row) == "COST_REDUCTION_APPROVED_FOR_MORE_TESTING"


def test_evaluate_cost_reduction_variant_blocks_low_sample():
    row = {"trades_count": 2, "baseline_trades_count": 20, "cost_reduction": 100, "return_delta": 0, "drawdown_delta": 0}

    assert evaluate_cost_reduction_variant(row) == "COST_REDUCTION_BLOCKED_LOW_SAMPLE"
