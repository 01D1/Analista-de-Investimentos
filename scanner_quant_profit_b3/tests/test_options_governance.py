from src.options.options_governance import evaluate_option_candidate, evaluate_structure_candidate


def test_option_governance_blocks_liquidity_and_spread():
    low_liq = evaluate_option_candidate({"option_type": "CALL", "strike": 30, "spread_pct": 3, "financial_volume": 100, "days_to_maturity": 30, "liquidity_score": 10})
    high_spread = evaluate_option_candidate({"option_type": "CALL", "strike": 30, "spread_pct": 30, "financial_volume": 100000, "days_to_maturity": 30, "liquidity_score": 80})
    high_risk = evaluate_option_candidate({"option_type": "CALL", "strike": 30, "spread_pct": 3, "financial_volume": 100000, "days_to_maturity": 30, "liquidity_score": 80, "risk_score": 10})

    assert low_liq["governance_status"] == "OPTION_BLOCKED_LIQUIDITY"
    assert high_spread["governance_status"] == "OPTION_BLOCKED_SPREAD"
    assert high_risk["governance_status"] == "OPTION_BLOCKED_RISK"


def test_structure_governance_blocks_risk_and_approves_study():
    blocked = evaluate_structure_candidate({"max_loss": float("inf"), "liquidity_score": 80, "risk_score": 80, "structure_score": 90})
    approved = evaluate_structure_candidate({"max_loss": 100, "liquidity_score": 80, "risk_score": 80, "structure_score": 80})

    assert blocked["governance_status"] == "STRUCTURE_BLOCKED_RISK"
    assert approved["governance_status"] == "STRUCTURE_APPROVED_FOR_STUDY"
