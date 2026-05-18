"""Indicadores tecnicos puros e tolerantes a series curtas."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _series(values) -> pd.Series:
    return pd.to_numeric(pd.Series(values), errors="coerce")


def sma(series, window: int) -> pd.Series:
    return _series(series).rolling(int(window), min_periods=1).mean()


def ema(series, window: int) -> pd.Series:
    return _series(series).ewm(span=int(window), adjust=False, min_periods=1).mean()


def rsi(close, window: int = 14) -> pd.Series:
    close = _series(close)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.mask((loss == 0) & (gain > 0), 100)
    out = out.mask((loss == 0) & (gain == 0), 50)
    return out.fillna(50)


def macd(close, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    close = _series(close)
    line = ema(close, fast) - ema(close, slow)
    signal_line = ema(line, signal)
    return pd.DataFrame(
        {
            "macd_line": line,
            "macd_signal": signal_line,
            "macd_hist": line - signal_line,
        }
    )


def atr(high, low, close, window: int = 14) -> pd.Series:
    high = _series(high)
    low = _series(low)
    close = _series(close)
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


def bollinger_bands(close, window: int = 20, num_std: float = 2) -> pd.DataFrame:
    close = _series(close)
    middle = sma(close, window)
    std = close.rolling(window, min_periods=1).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    width = ((upper - lower) / middle.replace(0, np.nan)) * 100
    return pd.DataFrame({"bb_middle": middle, "bb_upper": upper, "bb_lower": lower, "bb_width": width.fillna(0)})


def donchian_channels(high, low, window: int = 20) -> pd.DataFrame:
    high = _series(high)
    low = _series(low)
    return pd.DataFrame(
        {
            "donchian_high": high.rolling(window, min_periods=1).max(),
            "donchian_low": low.rolling(window, min_periods=1).min(),
        }
    )


def adx(high, low, close, window: int = 14) -> pd.Series:
    high = _series(high)
    low = _series(low)
    close = _series(close)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    tr = atr(high, low, close, window)
    plus_di = 100 * plus_dm.rolling(window, min_periods=1).mean() / tr.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(window, min_periods=1).mean() / tr.replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    return dx.rolling(window, min_periods=1).mean().fillna(0)


def vwap(price, volume) -> pd.Series:
    price = _series(price)
    volume = _series(volume).fillna(0)
    denom = volume.cumsum().replace(0, np.nan)
    return (price * volume).cumsum() / denom


def rolling_zscore(series, window: int = 20) -> pd.Series:
    series = _series(series)
    mean = series.rolling(window, min_periods=1).mean()
    std = series.rolling(window, min_periods=1).std(ddof=0).replace(0, np.nan)
    return ((series - mean) / std).replace([np.inf, -np.inf], np.nan).fillna(0)


def distance_from_ma(close, ma) -> pd.Series:
    close = _series(close)
    ma = _series(ma)
    return ((close - ma) / ma.replace(0, np.nan) * 100).replace([np.inf, -np.inf], np.nan)


def rate_of_change(close, window: int) -> pd.Series:
    return _series(close).pct_change(int(window)) * 100


def relative_volume(volume, window: int = 20) -> pd.Series:
    volume = _series(volume)
    base = volume.rolling(window, min_periods=1).mean().replace(0, np.nan)
    return (volume / base).replace([np.inf, -np.inf], np.nan)

