from src.paper.hypothesis_ranking_governance import evaluate_ranked_hypothesis


def test_ranked_hypothesis_governance_approves_observation():
    status = evaluate_ranked_hypothesis(
        {
            "hypothesis_robustness_score": 80,
            "useful_sources_count": 2,
            "positive_improvement_pct": 0.6,
            "mean_return_delta": 0.001,
            "mean_drawdown_delta": 0.001,
            "mean_fragility_delta": -2,
            "overfitting_flag": False,
            "cost_sensitivity_flag": False,
            "data_coverage_penalty": 0,
        }
    )
    assert status["governance_status"] == "HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION"


def test_ranked_hypothesis_governance_blocks_low_coverage():
    status = evaluate_ranked_hypothesis({"hypothesis_robustness_score": 80, "useful_sources_count": 0, "data_coverage_penalty": 40})
    assert status["governance_status"] == "HYPOTHESIS_RANK_BLOCKED_LOW_COVERAGE"

