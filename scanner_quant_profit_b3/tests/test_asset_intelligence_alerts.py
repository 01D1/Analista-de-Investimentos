import pandas as pd

from src.integration.asset_intelligence_alerts import build_alerts_from_asset_diffs


def test_asset_intelligence_alerts_for_material_changes():
    diffs = pd.DataFrame(
        {
            "ticker": ["PETR4"],
            "status_changed": [True],
            "governance_changed": [True],
            "valuation_changed": [True],
            "event_changed": [True],
            "regime_changed": [True],
            "score_delta": [-25],
            "data_quality_delta": [-30],
            "material_change_type": ["STATUS_CHANGE"],
            "explanation": ["PETR4 mudou para BLOQUEADO_GOVERNANCA"],
        }
    )
    alerts = build_alerts_from_asset_diffs(diffs)
    assert "ASSET_STATUS_CHANGED" in alerts["alert_type"].tolist()
    assert "ASSET_DATA_QUALITY_DROPPED" in alerts["alert_type"].tolist()
    assert "CRITICAL" in alerts["severity"].tolist()


def test_asset_intelligence_alerts_empty():
    assert build_alerts_from_asset_diffs(pd.DataFrame()).empty
