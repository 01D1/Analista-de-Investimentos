import pandas as pd

from src.db.init_db import init_database
from src.scanners import asset_intelligence_snapshot


def test_asset_intelligence_snapshot_cli_run(tmp_path, monkeypatch):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)

    def fake_build(**kwargs):
        return pd.DataFrame(
            {
                "ticker": ["PETR4"],
                "trade_date": ["2026-01-02"],
                "technical_score_final": [70],
                "quant_score": [72],
                "valuation_available": [False],
                "option_available": [False],
                "governance_blocked": [False],
                "integrated_status": ["APENAS_MONITORAR"],
                "integrated_score": [55],
                "integrated_confidence": ["BAIXA"],
                "integrated_governance_status": ["INTEGRATED_OBSERVATION_ONLY"],
                "data_quality_score": [40],
            }
        )

    monkeypatch.setattr(asset_intelligence_snapshot, "build_asset_intelligence_snapshot", fake_build)
    summary = asset_intelligence_snapshot.run(["PETR4"], save_db=True, csv=False, db_path=db)
    assert summary["assets_count"] == 1
    assert summary["rows_saved"] == 1


def test_asset_intelligence_snapshot_main_smoke(monkeypatch):
    monkeypatch.setattr(asset_intelligence_snapshot, "run", lambda **kwargs: {"assets_count": 0, "with_technical": 0, "with_quant": 0, "with_valuation": 0, "with_options": 0, "governance_blocked": 0, "high_convergence": 0, "insufficient_data": 0, "rows_saved": 0, "csv_path": ""})
    assert asset_intelligence_snapshot.main(["--tickers", "PETR4"]) == 0
