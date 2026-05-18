from src.paper.investigation_comparison import compare_investigation_to_base


def test_compare_investigation_to_base_improved():
    base = {"total_return": -0.01, "max_drawdown": -0.10, "profit_factor": 0.8, "win_rate": 0.4, "trades_count": 100, "fragility_score": 70, "cost_drag": 1000}
    inv = {"total_return": 0.03, "max_drawdown": -0.05, "profit_factor": 1.5, "win_rate": 0.55, "trades_count": 80, "fragility_score_after": 30, "cost_drag": 400}
    comparison = compare_investigation_to_base(base, inv)
    assert comparison["improved_return"] is True
    assert comparison["reduced_drawdown"] is True
    assert comparison["reduced_fragility"] is True
    assert comparison["conclusion"] == "INVESTIGATION_IMPROVED"


def test_compare_investigation_to_base_low_sample():
    comparison = compare_investigation_to_base({"trades_count": 100, "fragility_score": 50}, {"trades_count": 2, "fragility_score_after": 10})
    assert comparison["conclusion"] == "INVESTIGATION_INSUFFICIENT_DATA"
