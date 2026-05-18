from src.technical.technical_oos_governance import evaluate_technical_oos_candidate


def test_technical_oos_governance_approved_and_blocked():
    approved = evaluate_technical_oos_candidate({"windows_count": 6, "positive_windows_pct": 66, "mean_test_return": 0.3, "mean_test_hit_rate": 55, "avg_test_signals": 40, "overfitting_windows_pct": 0, "insufficient_windows_pct": 0})
    blocked = evaluate_technical_oos_candidate({"windows_count": 1, "positive_windows_pct": 0, "mean_test_return": 0, "mean_test_hit_rate": 0, "avg_test_signals": 0, "insufficient_windows_pct": 100})
    assert approved["governance_status"] == "TECH_OOS_APPROVED_FOR_STUDY"
    assert blocked["governance_status"] == "TECH_OOS_BLOCKED_INSUFFICIENT_DATA"
    assert approved["approved"] is False

