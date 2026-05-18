"""Features quantitativas de momentum."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.technical.indicators import macd, rate_of_change, rsi


def _one(group: pd.DataFrame) -> pd.DataFrame:
    out = group.sort_values("trade_date").copy()
    close = pd.to_numeric(out["close"], errors="coerce")
    for window in [1, 3, 5, 10, 20]:
        out[f"return_{window}d"] = close.pct_change(window) * 100
    out["rsi_14"] = rsi(close, 14)
    macd_df = macd(close)
    out[["macd_line", "macd_signal", "macd_hist"]] = macd_df
    out["roc_10"] = rate_of_change(close, 10)
    out["roc_20"] = rate_of_change(close, 20)
    raw = 50 + out["macd_hist"].fillna(0) * 8 + out["roc_10"].fillna(0) * 1.5 + (out["rsi_14"].fillna(50) - 50) * 0.6
    out["momentum_score"] = raw.clip(0, 100).round(2)
    out["momentum_state"] = np.select(
        [
            out["rsi_14"] >= 70,
            out["rsi_14"] <= 30,
            out["momentum_score"] >= 70,
            out["momentum_score"] >= 55,
            out["momentum_score"] < 45,
        ],
        ["SOBRECOMPRADO", "SOBREVENDA", "MOMENTUM_FORTE", "MOMENTUM_MODERADO", "MOMENTUM_FRACO"],
        default="INDEFINIDO",
    )
    return out


def calculate_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    if "ticker" in work.columns:
        return work.groupby("ticker", group_keys=False).apply(_one).reset_index(drop=True)
    return _one(work).reset_index(drop=True)

