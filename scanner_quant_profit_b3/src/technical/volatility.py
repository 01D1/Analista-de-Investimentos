"""Features objetivas de volatilidade."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.technical.indicators import atr, bollinger_bands, rolling_zscore


def _one(group: pd.DataFrame) -> pd.DataFrame:
    out = group.sort_values("trade_date").copy()
    close = pd.to_numeric(out["close"], errors="coerce")
    high = pd.to_numeric(out["high"], errors="coerce")
    low = pd.to_numeric(out["low"], errors="coerce")
    ret = close.pct_change()
    out["atr_14"] = atr(high, low, close, 14)
    out["atr_pct"] = (out["atr_14"] / close.replace(0, np.nan) * 100).replace([np.inf, -np.inf], np.nan)
    out["realized_vol_20"] = ret.rolling(20, min_periods=2).std(ddof=0) * np.sqrt(252) * 100
    out["realized_vol_60"] = ret.rolling(60, min_periods=2).std(ddof=0) * np.sqrt(252) * 100
    out["range_pct"] = ((high - low) / close.replace(0, np.nan) * 100).replace([np.inf, -np.inf], np.nan)
    bb = bollinger_bands(close)
    out[["bb_middle", "bb_upper", "bb_lower", "bb_width"]] = bb
    out["volatility_zscore"] = rolling_zscore(out["range_pct"], 20)
    out["volatility_regime"] = np.select(
        [
            out["volatility_zscore"] >= 1.5,
            out["volatility_zscore"] <= -1.0,
            out["bb_width"] > out["bb_width"].rolling(20, min_periods=1).mean() * 1.3,
            out["bb_width"] < out["bb_width"].rolling(20, min_periods=1).mean() * 0.7,
        ],
        ["ALTA_VOLATILIDADE", "BAIXA_VOLATILIDADE", "EXPANSAO_VOLATILIDADE", "COMPRESSAO_VOLATILIDADE"],
        default="NORMAL",
    )
    risk_penalty = (out["volatility_zscore"].fillna(0).clip(lower=0) * 15).clip(0, 50)
    out["volatility_score"] = (70 - risk_penalty + (out["volatility_regime"].eq("COMPRESSAO_VOLATILIDADE") * 10)).clip(0, 100).round(2)
    return out


def calculate_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    if "ticker" in work.columns:
        return work.groupby("ticker", group_keys=False).apply(_one).reset_index(drop=True)
    return _one(work).reset_index(drop=True)

