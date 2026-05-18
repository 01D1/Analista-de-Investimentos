import pandas as pd

from src.db.init_db import init_database
from src.integration.asset_intelligence_store import (
    load_asset_intelligence_history,
    load_latest_asset_intelligence_snapshot,
    save_asset_intelligence_snapshot,
)


def test_asset_intelligence_store_roundtrip(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    df = pd.DataFrame(
        {
            "trade_date": ["2026-01-02"],
            "ticker": ["PETR4"],
            "technical_score_final": [75],
            "quant_score": [80],
            "valuation_available": [True],
            "option_available": [False],
            "integrated_score": [70],
            "integrated_status": ["ASSIMETRIA_A_INVESTIGAR"],
            "integrated_confidence": ["MEDIA"],
            "integrated_governance_status": ["INTEGRATED_OBSERVATION_ONLY"],
            "data_quality_score": [65],
            "explanation": ["ativo em estudo"],
            "reasons_for": ['["camada positiva"]'],
            "reasons_against": ['["dados parciais"]'],
            "required_actions": ['["observar"]'],
        }
    )
    assert save_asset_intelligence_snapshot(db, df) == 1
    latest = load_latest_asset_intelligence_snapshot(db, ["PETR4"])
    history = load_asset_intelligence_history(db, "PETR4")
    assert latest.loc[0, "ticker"] == "PETR4"
    assert latest.loc[0, "integrated_status"] == "ASSIMETRIA_A_INVESTIGAR"
    assert len(history) == 1


def test_asset_intelligence_store_empty_missing_db(tmp_path):
    df = load_latest_asset_intelligence_snapshot(tmp_path / "missing.db", ["PETR4"])
    assert df.empty
    assert "integrated_status" in df.columns
