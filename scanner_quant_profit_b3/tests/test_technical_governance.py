from src.technical.technical_governance import evaluate_technical_setup_candidate


def test_technical_governance_blocks_insufficient_data_and_approves_for_study():
    blocked = evaluate_technical_setup_candidate({"signals": 5, "mean_return_5d": 1, "hit_rate_5d": 60})
    approved = evaluate_technical_setup_candidate({"signals": 50, "mean_return_5d": 1, "hit_rate_5d": 55})
    assert blocked["governance_status"] == "TECH_BLOCKED_INSUFFICIENT_DATA"
    assert approved["governance_status"] == "TECH_APPROVED_FOR_STUDY"
    assert approved["approved"] is False

