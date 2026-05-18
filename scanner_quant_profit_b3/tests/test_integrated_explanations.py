import json
import pandas as pd

from src.integration.integrated_explanations import (
    encode_list,
    generate_integrated_explanation,
    generate_reasons_against,
    generate_reasons_for,
    generate_required_actions,
)


def test_integrated_explanation_and_reasons():
    row = pd.Series(
        {
            "ticker": "PETR4",
            "integrated_status": "APENAS_MONITORAR",
            "technical_score_final": 70,
            "quant_score": 72,
            "valuation_available": False,
            "data_quality_score": 35,
            "event_governance_status": "EVENT_COVERAGE_WEAK",
        }
    )
    assert "PETR4" in generate_integrated_explanation(row)
    assert generate_reasons_for(row)
    assert "Valuation/fundamentos" in generate_reasons_against(row)[0]
    assert generate_required_actions(row)


def test_encode_list_json():
    encoded = encode_list(["a", "b"])
    assert json.loads(encoded) == ["a", "b"]
