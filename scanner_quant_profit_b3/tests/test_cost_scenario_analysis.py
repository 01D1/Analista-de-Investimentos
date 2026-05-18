import pandas as pd

from src.paper.cost_scenario_analysis import analyze_cost_sensitivity, build_cost_scenarios


def test_build_cost_scenarios():
    scenarios = build_cost_scenarios()
    assert "COST_STRESS" in scenarios["scenario_name"].tolist()


def test_analyze_cost_sensitivity_classifies():
    results = pd.DataFrame(
        {
            "scenario_name": ["COST_LOW", "COST_LOW", "COST_HIGH", "COST_HIGH"],
            "cost_bps": [5, 5, 20, 20],
            "slippage_bps": [2, 2, 10, 10],
            "total_return": [0.03, 0.02, -0.01, -0.02],
            "max_drawdown": [-0.02, -0.03, -0.05, -0.04],
            "profit_factor": [1.5, 1.4, 0.8, 0.7],
        }
    )
    out = analyze_cost_sensitivity(results)
    assert "COST_FRAGILE" in out["cost_robustness_class"].tolist()
