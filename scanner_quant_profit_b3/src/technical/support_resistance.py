"""Suporte, resistencia e rompimentos definidos por janelas objetivas."""
from __future__ import annotations

import pandas as pd

from src.technical.indicators import distance_from_ma, sma


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df.get(col), errors="coerce")


def calculate_support_resistance(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    windows = windows or [20, 50, 100]
    out = df.copy()
    high = _num(out, "high")
    low = _num(out, "low")
    close = _num(out, "close")
    for window in windows:
        out[f"high_{window}"] = high.rolling(window, min_periods=1).max()
        out[f"low_{window}"] = low.rolling(window, min_periods=1).min()
        out[f"distance_to_high_{window}"] = distance_from_ma(close, out[f"high_{window}"])
        out[f"distance_to_low_{window}"] = distance_from_ma(close, out[f"low_{window}"])
    return out


def detect_breakout(df: pd.DataFrame, window: int = 20, volume_confirmation: bool = True) -> pd.Series:
    close = _num(df, "close")
    prior_high = _num(df, "high").shift(1).rolling(window, min_periods=1).max()
    signal = close > prior_high
    if volume_confirmation and "volume" in df.columns:
        volume = _num(df, "volume")
        signal &= volume > 1.5 * sma(volume, 20)
    return signal.fillna(False)


def detect_breakdown(df: pd.DataFrame, window: int = 20, volume_confirmation: bool = True) -> pd.Series:
    close = _num(df, "close")
    prior_low = _num(df, "low").shift(1).rolling(window, min_periods=1).min()
    signal = close < prior_low
    if volume_confirmation and "volume" in df.columns:
        volume = _num(df, "volume")
        signal &= volume > 1.5 * sma(volume, 20)
    return signal.fillna(False)


def detect_near_support(df: pd.DataFrame, window: int = 20, tolerance_pct: float = 2) -> pd.Series:
    close = _num(df, "close")
    support = _num(df, "low").rolling(window, min_periods=1).min()
    return ((close - support).abs() / support.replace(0, pd.NA) * 100 <= tolerance_pct).fillna(False)


def detect_near_resistance(df: pd.DataFrame, window: int = 20, tolerance_pct: float = 2) -> pd.Series:
    close = _num(df, "close")
    resistance = _num(df, "high").rolling(window, min_periods=1).max()
    return ((close - resistance).abs() / resistance.replace(0, pd.NA) * 100 <= tolerance_pct).fillna(False)

