import pandas as pd

from src.integration.integrated_governance import evaluate_integrated_governance


def test_integrated_governance_blocks_low_data_quality():
    review = evaluate_integrated_governance(pd.Series({"ticker": "PETR4", "data_quality_score": 20}))
    assert review["integrated_governance_status"] == "INTEGRATED_BLOCKED_DATA"
    assert review["confidence_level"] == "BAIXA"


def test_integrated_governance_blocks_layer_governance():
    review = evaluate_integrated_governance(
        pd.Series({"ticker": "PETR4", "data_quality_score": 80, "technical_oos_status": "TECH_OOS_BLOCKED_INSUFFICIENT_DATA"})
    )
    assert review["integrated_governance_status"] == "INTEGRATED_BLOCKED_GOVERNANCE"


def test_integrated_governance_blocks_risk_status():
    review = evaluate_integrated_governance(
        pd.Series({"ticker": "PETR4", "data_quality_score": 80, "risk_status": "RISK_BLOCKED_VAR"})
    )
    assert review["integrated_governance_status"] == "INTEGRATED_BLOCKED_GOVERNANCE"


def test_integrated_governance_approved_for_study_is_not_operational():
    review = evaluate_integrated_governance(
        pd.Series(
            {
                "ticker": "PETR4",
                "data_quality_score": 90,
                "technical_score_final": 80,
                "quant_score": 75,
                "valuation_available": True,
                "upside_pct": 12,
                "regime_governance_status": "REGIME_OK",
            }
        )
    )
    assert review["integrated_governance_status"] == "INTEGRATED_APPROVED_FOR_STUDY"
    assert review["approved_for_study"] is False
