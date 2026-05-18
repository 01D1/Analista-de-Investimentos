from src.paper.hypothesis_oos_governance import evaluate_hypothesis_oos_governance


def test_hypothesis_oos_governance_approved_for_observation():
    review = evaluate_hypothesis_oos_governance(
        {
            "windows_count": 2,
            "scenarios_count": 4,
            "positive_improvement_pct": 0.75,
            "mean_return_delta": 0.02,
            "mean_drawdown_delta": 0.01,
            "mean_fragility_delta": -5,
            "cost_sensitive_pct": 0.0,
            "regime_instability_pct": 0.0,
            "overfitting_pct": 0.0,
        }
    )
    assert review["governance_status"] == "HYPOTHESIS_APPROVED_FOR_RECURRENT_OBSERVATION"


def test_hypothesis_oos_governance_blocks_low_sample():
    review = evaluate_hypothesis_oos_governance({"windows_count": 0, "scenarios_count": 0})
    assert review["governance_status"] == "HYPOTHESIS_BLOCKED_LOW_SAMPLE"
