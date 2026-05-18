"""Modelos de volatilidade para risco analitico."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _s(x) -> pd.Series:
    return pd.to_numeric(pd.Series(x), errors="coerce")


def _ann(value, annualize: bool):
    return value * np.sqrt(TRADING_DAYS) if annualize else value


def calculate_close_to_close_vol(returns, window, annualize: bool = True):
    vol = _s(returns).rolling(window).std()
    return _ann(vol, annualize)


def calculate_realized_volatility(returns, window: int = 20, annualize: bool = True):
    return calculate_close_to_close_vol(returns, window, annualize)


def calculate_ewma_volatility(returns, lambda_: float = 0.94, annualize: bool = True):
    r = _s(returns).fillna(0)
    var = r.pow(2).ewm(alpha=1 - lambda_, adjust=False).mean()
    vol = np.sqrt(var)
    return _ann(vol, annualize)


def calculate_downside_volatility(returns, window: int = 20, annualize: bool = True):
    r = _s(returns)
    downside = r.where(r < 0, 0)
    vol = downside.rolling(window).std()
    return _ann(vol, annualize)


def calculate_parkinson_volatility(high, low, window: int = 20, annualize: bool = True):
    h = _s(high)
    l = _s(low).replace(0, np.nan)
    rs = np.log(h / l).pow(2) / (4 * np.log(2))
    vol = np.sqrt(rs.rolling(window).mean())
    return _ann(vol, annualize)


def calculate_garman_klass_volatility(open_, high, low, close, window: int = 20, annualize: bool = True):
    o = _s(open_).replace(0, np.nan)
    h = _s(high)
    l = _s(low).replace(0, np.nan)
    c = _s(close).replace(0, np.nan)
    term = 0.5 * np.log(h / l).pow(2) - (2 * np.log(2) - 1) * np.log(c / o).pow(2)
    vol = np.sqrt(term.clip(lower=0).rolling(window).mean())
    return _ann(vol, annualize)


def calculate_atr_volatility(high, low, close, window: int = 14):
    h = _s(high)
    l = _s(low)
    c = _s(close)
    prev_close = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(window).mean()
    return atr / c.replace(0, np.nan)


def calculate_volatility_ensemble(vol_df: pd.DataFrame):
    cols = [c for c in ["vol_20d", "vol_60d", "vol_ewma", "downside_vol", "parkinson_vol", "garman_klass_vol", "atr_vol"] if c in vol_df.columns]
    if not cols:
        return pd.Series(np.nan, index=vol_df.index)
    return vol_df[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)


def classify_volatility_regime(row) -> str:
    vol = pd.to_numeric(pd.Series([row.get("ensemble_vol")]), errors="coerce").iloc[0]
    vol20 = pd.to_numeric(pd.Series([row.get("vol_20d")]), errors="coerce").iloc[0]
    vol60 = pd.to_numeric(pd.Series([row.get("vol_60d")]), errors="coerce").iloc[0]
    ewma = pd.to_numeric(pd.Series([row.get("vol_ewma")]), errors="coerce").iloc[0]
    if pd.isna(vol):
        return "DADOS_INSUFICIENTES"
    if pd.notna(vol20) and pd.notna(vol60):
        if vol20 > vol60 * 1.5:
            return "VOL_EXPANDINDO"
        if vol20 < vol60 * 0.65:
            return "VOL_COMPRIMINDO"
    if pd.notna(ewma) and pd.notna(vol60) and ewma > vol60 * 1.8:
        return "VOL_EXTREMA"
    if vol >= 0.60:
        return "VOL_EXTREMA"
    if vol >= 0.35:
        return "VOL_ALTA"
    if vol <= 0.15:
        return "VOL_BAIXA"
    return "VOL_NORMAL"


def calculate_volatility_features(price_df: pd.DataFrame) -> pd.DataFrame:
    work = price_df.copy().sort_values("trade_date")
    returns = work["close"].pct_change()
    out = work[["trade_date", "ticker"]].copy() if "ticker" in work.columns else work[["trade_date"]].copy()
    for window in [5, 10, 20, 60, 252]:
        out[f"vol_{window}d"] = calculate_realized_volatility(returns, window)
    out["vol_ewma"] = calculate_ewma_volatility(returns)
    out["downside_vol"] = calculate_downside_volatility(returns)
    out["parkinson_vol"] = calculate_parkinson_volatility(work["high"], work["low"])
    out["garman_klass_vol"] = calculate_garman_klass_volatility(work["open"], work["high"], work["low"], work["close"])
    out["atr_vol"] = calculate_atr_volatility(work["high"], work["low"], work["close"])
    out["ensemble_vol"] = calculate_volatility_ensemble(out)
    out["volatility_regime"] = out.apply(classify_volatility_regime, axis=1)
    return out

