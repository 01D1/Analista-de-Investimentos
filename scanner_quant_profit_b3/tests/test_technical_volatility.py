from tests.technical_fixtures import sample_price_df
from src.technical.volatility import calculate_volatility_features


def test_volatility_features_include_atr_and_regime():
    out = calculate_volatility_features(sample_price_df())
    assert "atr_14" in out.columns
    assert "volatility_regime" in out.columns
    assert out["volatility_score"].notna().any()

