from src.paper.paper_oos_governance import evaluate_paper_oos_governance


def test_paper_oos_governance_approved_for_study():
    review = evaluate_paper_oos_governance({"windows_count": 3, "positive_windows_pct": 0.67, "mean_test_return": 0.02, "mean_test_drawdown": -0.05, "avg_test_trades": 12, "overfitting_windows_pct": 0})
    assert review["governance_status"] == "PAPER_OOS_APPROVED_FOR_STUDY"


def test_paper_oos_governance_blocks_overfitting():
    review = evaluate_paper_oos_governance({"windows_count": 3, "positive_windows_pct": 0.33, "mean_test_return": 0.01, "mean_test_drawdown": -0.05, "avg_test_trades": 12, "overfitting_windows_pct": 0.5})
    assert review["governance_status"] == "PAPER_OOS_BLOCKED_OVERFITTING"
