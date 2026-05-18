from src.risk.risk_governance import evaluate_risk_snapshot, generate_risk_governance_report


def test_risk_governance_ok():
    review = evaluate_risk_snapshot(
        {
            "ensemble_vol": 0.20,
            "parametric_var_95": 100,
            "position_value": 10_000,
            "recommended_size": 100,
            "volatility_regime": "VOL_NORMAL",
        }
    )
    assert review["risk_status"] == "RISK_OK"


def test_risk_governance_blocks_high_var():
    review = evaluate_risk_snapshot(
        {
            "ensemble_vol": 0.30,
            "parametric_var_95": 700,
            "position_value": 10_000,
            "recommended_size": 100,
            "volatility_regime": "VOL_NORMAL",
        }
    )
    assert review["risk_status"] == "RISK_BLOCKED_VAR"
    assert "Status de risco" in generate_risk_governance_report(review)


def test_risk_governance_blocks_data():
    review = evaluate_risk_snapshot({"ensemble_vol": None, "position_value": 0})
    assert review["risk_status"] == "RISK_BLOCKED_DATA"
