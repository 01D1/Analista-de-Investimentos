import pandas as pd

from src.db.init_db import init_database
from src.integration.asset_intelligence_diff_store import (
    load_asset_intelligence_diff_history,
    load_latest_asset_intelligence_diffs,
    save_asset_intelligence_diffs,
)


def test_asset_intelligence_diff_store_roundtrip(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    diffs = pd.DataFrame(
        {
            "ticker": ["PETR4"],
            "previous_snapshot_id": [1],
            "current_snapshot_id": [2],
            "previous_created_at": ["2026-01-01"],
            "current_created_at": ["2026-01-02"],
            "changes_count": [1],
            "changed_fields": [["integrated_status"]],
            "score_delta": [-20],
            "data_quality_delta": [0],
            "status_changed": [True],
            "governance_changed": [False],
            "valuation_changed": [False],
            "technical_changed": [False],
            "quant_changed": [False],
            "event_changed": [False],
            "regime_changed": [False],
            "options_changed": [False],
            "material_change": [True],
            "material_change_type": ["STATUS_CHANGE"],
            "explanation": ["mudança analítica"],
            "metadata_json": ["{}"],
        }
    )
    assert save_asset_intelligence_diffs(db, diffs) == 1
    latest = load_latest_asset_intelligence_diffs(db, ["PETR4"])
    history = load_asset_intelligence_diff_history(db, "PETR4")
    assert latest.loc[0, "material_change_type"] == "STATUS_CHANGE"
    assert len(history) == 1


def test_asset_intelligence_diff_store_missing_db(tmp_path):
    df = load_latest_asset_intelligence_diffs(tmp_path / "missing.db")
    assert df.empty
    assert "material_change_type" in df.columns
