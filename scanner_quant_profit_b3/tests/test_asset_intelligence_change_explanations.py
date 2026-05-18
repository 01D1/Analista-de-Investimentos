import json
import pandas as pd

from src.integration.asset_intelligence_change_explanations import (
    explain_asset_change,
    explain_event_change,
    explain_governance_change,
    explain_regime_change,
    explain_score_change,
    explain_valuation_change,
)


def test_change_explanations_are_analytical():
    row = pd.Series(
        {
            "ticker": "PETR4",
            "score_delta": -17,
            "status_changed": True,
            "governance_changed": True,
            "valuation_changed": True,
            "event_changed": True,
            "regime_changed": True,
            "options_changed": False,
            "data_quality_delta": -5,
            "metadata_json": json.dumps(
                {
                    "field_changes": {
                        "integrated_status": {"previous": "APENAS_MONITORAR", "current": "BLOQUEADO_GOVERNANCA"},
                        "integrated_governance_status": {"previous": "INTEGRATED_OBSERVATION_ONLY", "current": "INTEGRATED_BLOCKED_GOVERNANCE"},
                        "upside_pct": {"previous": 10, "current": 22},
                        "event_type": {"previous": None, "current": "RESULTADO"},
                        "primary_regime": {"previous": "LATERAL", "current": "RISCO_ELEVADO"},
                    }
                }
            ),
        }
    )
    text = explain_asset_change(row)
    assert "PETR4 mudou" in text
    assert "não constitui recomendação" in text
    assert "caiu" in explain_score_change(row)
    assert "governança integrada mudou" in explain_governance_change(row).lower()
    assert "upside mudou" in explain_valuation_change(row).lower()
    assert "eventos mudou" in explain_event_change(row).lower()
    assert "regime principal mudou" in explain_regime_change(row).lower()
