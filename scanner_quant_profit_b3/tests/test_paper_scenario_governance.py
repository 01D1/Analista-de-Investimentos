from src.paper.paper_scenario_governance import evaluate_multi_scenario_governance


def test_multi_scenario_governance_blocks_low_sample():
    review = evaluate_multi_scenario_governance({"periods_count": 1, "scenarios_count": 2})
    assert review["governance_status"] == "PAPER_SCENARIO_BLOCKED_LOW_SAMPLE"


def test_multi_scenario_governance_robust_for_study():
    review = evaluate_multi_scenario_governance({"periods_count": 3, "scenarios_count": 5, "signal_sources_count": 2, "positive_periods_pct": 0.7, "mean_return": 0.02, "mean_drawdown": -0.05, "cost_robustness_class": "COST_ROBUST"})
    assert review["governance_status"] == "PAPER_SCENARIO_ROBUST_FOR_STUDY"
