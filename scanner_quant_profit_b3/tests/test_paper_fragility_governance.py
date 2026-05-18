from src.paper.paper_fragility_governance import evaluate_fragility_governance


def test_fragility_governance_blocks_cost_and_data():
    assert evaluate_fragility_governance({"total_trades": 1})["governance_status"] == "PAPER_FRAGILITY_BLOCKED_DATA"
    assert evaluate_fragility_governance({"total_trades": 10, "cost_drag_pct": 0.8})["governance_status"] == "PAPER_FRAGILITY_BLOCKED_COST"
