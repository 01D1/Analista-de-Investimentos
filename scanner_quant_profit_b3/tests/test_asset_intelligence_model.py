import pandas as pd

from src.integration.asset_intelligence_model import INTEGRATED_STATUSES, empty_asset_intelligence_frame, normalize_asset_intelligence_frame


def test_asset_intelligence_model_schema():
    df = empty_asset_intelligence_frame()
    assert df.empty
    assert "ticker" in df.columns
    assert "integrated_status" in df.columns
    assert "ALTA_CONVERGENCIA_ANALITICA" in INTEGRATED_STATUSES


def test_normalize_asset_intelligence_frame_adds_missing_columns():
    df = normalize_asset_intelligence_frame(pd.DataFrame({"ticker": ["PETR4"]}))
    assert df.loc[0, "ticker"] == "PETR4"
    assert "technical_score_final" in df.columns
    assert pd.isna(df.loc[0, "integrated_score"])
