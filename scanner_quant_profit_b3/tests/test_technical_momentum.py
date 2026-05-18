from tests.technical_fixtures import sample_price_df
from src.technical.momentum import calculate_momentum_features


def test_momentum_features_include_rsi_and_macd():
    out = calculate_momentum_features(sample_price_df())
    assert "rsi_14" in out.columns
    assert "macd_hist" in out.columns
    assert out.iloc[-1]["momentum_score"] > 50

