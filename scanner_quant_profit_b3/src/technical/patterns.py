"""Padroes tecnicos objetivos, sem nomenclatura subjetiva."""
from __future__ import annotations

import pandas as pd


def _n(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df.get(col), errors="coerce")


def detect_inside_bar(df: pd.DataFrame) -> pd.Series:
    high, low = _n(df, "high"), _n(df, "low")
    return ((high < high.shift(1)) & (low > low.shift(1))).fillna(False)


def detect_outside_bar(df: pd.DataFrame) -> pd.Series:
    high, low = _n(df, "high"), _n(df, "low")
    return ((high > high.shift(1)) & (low < low.shift(1))).fillna(False)


def detect_wide_range_bar(df: pd.DataFrame) -> pd.Series:
    rng = (_n(df, "high") - _n(df, "low")).abs()
    return (rng > 1.5 * rng.rolling(20, min_periods=1).mean()).fillna(False)


def detect_gap_up(df: pd.DataFrame) -> pd.Series:
    return (_n(df, "open") > _n(df, "high").shift(1)).fillna(False)


def detect_gap_down(df: pd.DataFrame) -> pd.Series:
    return (_n(df, "open") < _n(df, "low").shift(1)).fillna(False)


def detect_reversal_candle(df: pd.DataFrame) -> pd.Series:
    open_, high, low, close = _n(df, "open"), _n(df, "high"), _n(df, "low"), _n(df, "close")
    body = (close - open_).abs()
    lower_shadow = pd.concat([open_, close], axis=1).min(axis=1) - low
    upper_shadow = high - pd.concat([open_, close], axis=1).max(axis=1)
    return (((lower_shadow > 2 * body) & (close > open_)) | ((upper_shadow > 2 * body) & (close < open_))).fillna(False)


def detect_strength_candle(df: pd.DataFrame) -> pd.Series:
    open_, high, low, close = _n(df, "open"), _n(df, "high"), _n(df, "low"), _n(df, "close")
    rng = (high - low).replace(0, pd.NA)
    volume = _n(df, "volume") if "volume" in df.columns else pd.Series(1, index=df.index)
    near_high = (high - close) / rng <= 0.25
    wide = (high - low) > (high - low).rolling(20, min_periods=1).mean()
    vol_ok = volume > volume.rolling(20, min_periods=1).mean()
    return (near_high & wide & vol_ok & (close > open_)).fillna(False)


def detect_rejection_candle(df: pd.DataFrame) -> pd.Series:
    open_, high, low, close = _n(df, "open"), _n(df, "high"), _n(df, "low"), _n(df, "close")
    rng = (high - low).replace(0, pd.NA)
    lower_shadow = pd.concat([open_, close], axis=1).min(axis=1) - low
    upper_shadow = high - pd.concat([open_, close], axis=1).max(axis=1)
    return (((lower_shadow / rng) >= 0.5) | ((upper_shadow / rng) >= 0.5)).fillna(False)

