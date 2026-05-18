from src.paper.investigation_governance import evaluate_investigation_result


def test_investigation_governance_approved_for_further_test():
    review = evaluate_investigation_result(
        {
            "improvement_score": 45,
            "simulated_trades": 50,
            "improved_return": True,
            "reduced_drawdown": True,
            "reduced_fragility": True,
        }
    )
    assert review["governance_status"] == "INVESTIGATION_APPROVED_FOR_FURTHER_TEST"


def test_investigation_governance_blocks_low_sample():
    review = evaluate_investigation_result({"improvement_score": 80, "simulated_trades": 3})
    assert review["governance_status"] == "INVESTIGATION_BLOCKED_LOW_SAMPLE"
