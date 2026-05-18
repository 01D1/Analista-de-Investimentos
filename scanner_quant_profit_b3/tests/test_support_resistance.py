from tests.technical_fixtures import sample_price_df
from src.technical.support_resistance import calculate_support_resistance, detect_breakout


def test_support_resistance_and_breakout():
    df = sample_price_df()
    out = calculate_support_resistance(df)
    assert "high_20" in out.columns
    breakout = detect_breakout(df, window=20)
    assert bool(breakout.iloc[-1])

