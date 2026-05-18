from src.paper.hypothesis_deep_governance import evaluate_deep_hypothesis_governance


def test_deep_governance_approves_only_for_observation():
    status = evaluate_deep_hypothesis_governance(
        {
            "positive_improvement_pct": 0.7,
            "mean_return_delta": 0.001,
            "mean_drawdown_delta": 0.0,
            "mean_fragility_delta": -3,
            "useful_sources_count": 2,
            "useful_regimes_count": 2,
            "asset_concentration_pct": 0.2,
        }
    )
    assert status == "HYPOTHESIS_DEEP_APPROVED_FOR_OBSERVATION"


def test_deep_governance_blocks_cost():
    assert evaluate_deep_hypothesis_governance({"primary_block_reason": "BLOCKED_BY_COST"}) == "HYPOTHESIS_DEEP_BLOCKED_COST"
