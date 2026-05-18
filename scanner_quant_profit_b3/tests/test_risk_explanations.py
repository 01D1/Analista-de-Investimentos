from src.risk.risk_explanations import explain_risk_governance, explain_sizing, explain_var, explain_volatility


def test_risk_explanations_are_analytical():
    row = {
        "volatility_regime": "VOL_ALTA",
        "ensemble_vol": 0.40,
        "parametric_var_95": 120,
        "position_value": 10_000,
        "limiting_factor": "VAR",
        "recommended_size": 50,
        "risk_status": "RISK_WARNING",
    }
    text = explain_volatility(row) + explain_var(row) + explain_sizing(row) + explain_risk_governance(row)
    assert "Sizing sugerido para estudo" in text
    assert "Governança de risco" in text
