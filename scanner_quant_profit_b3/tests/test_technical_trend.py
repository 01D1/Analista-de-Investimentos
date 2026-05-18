from tests.technical_fixtures import sample_price_df
from src.technical.trend import calculate_trend_features


def test_trend_features_classify_uptrend():
    out = calculate_trend_features(sample_price_df())
    assert "trend_strength_score" in out.columns
    assert out.iloc[-1]["trend_short"] == "ALTA_TENDENCIAL"

