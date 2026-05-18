import pandas as pd

from src.technical.indicators import atr, bollinger_bands, ema, macd, relative_volume, rsi, sma


def test_basic_indicators_handle_short_series():
    close = pd.Series([10, 11, 12, 13])
    assert sma(close, 3).iloc[-1] == 12
    assert ema(close, 3).notna().all()
    assert rsi(close, 14).iloc[-1] >= 50
    assert "macd_hist" in macd(close).columns
    assert atr(close + 1, close - 1, close).iloc[-1] > 0
    assert bollinger_bands(close).loc[3, "bb_upper"] >= close.iloc[-1]
    assert relative_volume(pd.Series([100, 100, 200]), 2).iloc[-1] > 1

