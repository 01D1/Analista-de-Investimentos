import pandas as pd

from src.paper.cost_reduction_comparison import compare_cost_variant_to_baseline


def test_compare_cost_variant_to_baseline_detects_improvement():
    baseline = pd.DataFrame([{"total_return": 0.01, "max_drawdown": -0.05, "cost_drag_total": 100, "exit_cost": 50, "rebalance_cost": 40, "turnover": 10, "trades_count": 10, "profit_factor": 1}])
    variant = pd.DataFrame([{"total_return": 0.011, "max_drawdown": -0.04, "cost_drag_total": 80, "exit_cost": 45, "rebalance_cost": 25, "turnover": 8, "trades_count": 9, "profit_factor": 1.2}])

    out = compare_cost_variant_to_baseline(baseline, variant)

    assert out["cost_drag_delta"] == -20
    assert out["comparison_class"] == "COST_VARIANT_IMPROVED"
