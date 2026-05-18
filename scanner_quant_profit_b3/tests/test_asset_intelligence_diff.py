import pandas as pd

from src.integration.asset_intelligence_diff import compare_asset_snapshots, compare_latest_snapshots, detect_material_changes


def _row(snapshot_id, created_at, status="APENAS_MONITORAR", score=55, gov="INTEGRATED_OBSERVATION_ONLY", upside=10, regime="LATERAL"):
    return pd.Series(
        {
            "id": snapshot_id,
            "ticker": "PETR4",
            "created_at": created_at,
            "integrated_score": score,
            "integrated_status": status,
            "integrated_governance_status": gov,
            "data_quality_score": 60,
            "upside_pct": upside,
            "primary_regime": regime,
        }
    )


def test_compare_asset_snapshots_without_material_change():
    diff = compare_asset_snapshots(_row(1, "2026-01-01"), _row(2, "2026-01-02"))
    assert diff["changes_count"] == 0
    assert diff["material_change_type"] == "NO_MATERIAL_CHANGE"


def test_compare_asset_snapshots_status_and_governance_change():
    diff = compare_asset_snapshots(
        _row(1, "2026-01-01", status="APENAS_MONITORAR", score=65),
        _row(2, "2026-01-02", status="BLOQUEADO_GOVERNANCA", score=45, gov="INTEGRATED_BLOCKED_GOVERNANCE"),
    )
    assert diff["status_changed"] is True
    assert diff["governance_changed"] is True
    assert diff["material_change_type"] == "STATUS_CHANGE"
    assert diff["score_delta"] == -20


def test_compare_latest_snapshots_by_ticker():
    df = pd.DataFrame([_row(1, "2026-01-01"), _row(2, "2026-01-02", score=70)])
    diffs = compare_latest_snapshots(df)
    assert len(diffs) == 1
    assert diffs.loc[0, "ticker"] == "PETR4"


def test_detect_material_changes_score_threshold():
    df = pd.DataFrame({"status_changed": [False], "governance_changed": [False], "score_delta": [12], "data_quality_delta": [0], "valuation_changed": [False], "event_changed": [False], "regime_changed": [False], "options_changed": [False], "material_change_type": ["NO_MATERIAL_CHANGE"]})
    out = detect_material_changes(df)
    assert bool(out.loc[0, "material_change"]) is True
