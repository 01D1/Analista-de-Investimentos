from tests.technical_fixtures import sample_price_df
from src.technical.patterns import detect_strength_candle, detect_wide_range_bar


def test_patterns_return_boolean_series():
    df = sample_price_df()
    assert detect_wide_range_bar(df).dtype == bool
    assert detect_strength_candle(df).dtype == bool

