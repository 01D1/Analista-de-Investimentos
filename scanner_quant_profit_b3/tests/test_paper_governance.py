from src.paper.paper_governance import evaluate_paper_simulation


def test_paper_governance_blocks_low_sample():
    review = evaluate_paper_simulation({"trades_count": 1, "total_return": 0.1, "max_drawdown": 0.01})
    assert review["governance_status"] == "PAPER_BLOCKED_LOW_SAMPLE"


def test_paper_governance_approved_for_review():
    review = evaluate_paper_simulation({"trades_count": 10, "total_return": 0.1, "max_drawdown": -0.05, "turnover": 10})
    assert review["governance_status"] == "PAPER_APPROVED_FOR_REVIEW"


def test_paper_governance_advanced_statuses():
    low_sample = evaluate_paper_simulation({"trades_count": 5, "total_return": 0.1, "max_drawdown": -0.02, "advanced_rules": True})
    improved = evaluate_paper_simulation({"trades_count": 20, "total_return": 0.1, "max_drawdown": -0.02, "advanced_rules": True})
    overtrade = evaluate_paper_simulation({"trades_count": 20, "total_return": 0.1, "max_drawdown": -0.02, "advanced_rules": True, "exit_events_count": 50})
    assert low_sample["governance_status"] == "PAPER_REQUIRES_MORE_DATA"
    assert improved["governance_status"] == "PAPER_ADVANCED_RULES_IMPROVED"
    assert overtrade["governance_status"] == "PAPER_BLOCKED_OVERTRADING"
