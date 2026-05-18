import pandas as pd

from src.db.init_db import init_database
from src.integration.asset_intelligence_store import save_asset_intelligence_snapshot
from src.scanners import asset_intelligence_diff


def test_asset_intelligence_diff_cli_with_synthetic_snapshots(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    first = pd.DataFrame(
        {
            "trade_date": ["2026-01-01"],
            "ticker": ["PETR4"],
            "integrated_score": [65],
            "integrated_status": ["APENAS_MONITORAR"],
            "integrated_governance_status": ["INTEGRATED_OBSERVATION_ONLY"],
            "data_quality_score": [60],
        }
    )
    second = first.copy()
    second["integrated_score"] = [40]
    second["integrated_status"] = ["BLOQUEADO_GOVERNANCA"]
    second["integrated_governance_status"] = ["INTEGRATED_BLOCKED_GOVERNANCE"]
    save_asset_intelligence_snapshot(db, first)
    save_asset_intelligence_snapshot(db, second)

    result = asset_intelligence_diff.run(save_db=True, csv=False, db_path=db)
    assert result["diffs_count"] == 1
    assert result["material_changes"] == 1
    assert result["rows_saved"] == 1


def test_asset_intelligence_diff_cli_main(monkeypatch):
    monkeypatch.setattr(asset_intelligence_diff, "run", lambda **kwargs: {"snapshots_count": 0, "diffs_count": 0, "material_changes": 0, "governance_changes": 0, "status_changes": 0, "valuation_changes": 0, "regime_changes": 0, "rows_saved": 0, "alerts_saved": 0, "csv_path": ""})
    assert asset_intelligence_diff.main(["--latest"]) == 0
