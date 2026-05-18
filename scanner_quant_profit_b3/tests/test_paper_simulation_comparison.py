import pandas as pd

from src.paper.simulation_comparison import compare_paper_simulations, generate_simulation_comparison_report


def test_compare_paper_simulations_detects_improvement():
    simple = {"capital_final": 99_000, "total_return": -0.01, "max_drawdown": -0.10, "profit_factor": 0.8, "governance_status": "PAPER_BLOCKED_NEGATIVE_RETURN"}
    advanced = {"capital_final": 104_000, "total_return": 0.04, "max_drawdown": -0.08, "profit_factor": 1.4, "governance_status": "PAPER_ADVANCED_RULES_IMPROVED"}
    comparison = compare_paper_simulations(simple, advanced)
    assert "total_return" in comparison["metric"].tolist()
    assert bool(comparison[comparison["metric"] == "total_return"]["improved"].iloc[0])
    assert bool(comparison[comparison["metric"] == "governance_status"]["material_change"].iloc[0])
    assert "simple vs advanced" in generate_simulation_comparison_report(comparison)


def test_compare_accepts_series_rows():
    comparison = compare_paper_simulations(pd.Series({"total_return": 0}), pd.Series({"total_return": 0.02}))
    assert not comparison.empty
