"""Features objetivas de tendencia."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.technical.indicators import distance_from_ma, ema, sma


def _state(score: float, slope: float) -> str:
    if pd.isna(score) or pd.isna(slope):
        return "INDEFINIDO"
    if score >= 70 and slope > 0:
        return "ALTA_TENDENCIAL"
    if score <= 30 and slope < 0:
        return "BAIXA_TENDENCIAL"
    if abs(slope) < 0.05:
        return "LATERAL"
    return "TENDENCIA_FRACA"


def _features_one(group: pd.DataFrame) -> pd.DataFrame:
    out = group.sort_values("trade_date").copy()
    close = pd.to_numeric(out["close"], errors="coerce")
    out["sma_20"] = sma(close, 20)
    out["sma_50"] = sma(close, 50)
    out["sma_200"] = sma(close, 200)
    out["ema_9"] = ema(close, 9)
    out["ema_21"] = ema(close, 21)
    out["ema_50"] = ema(close, 50)
    for col in ["sma20", "sma50", "sma200"]:
        ma_col = f"sma_{col.replace('sma', '')}"
        out[f"close_above_{col}"] = (close > out[ma_col]).astype(int)
    out["ema9_above_ema21"] = (out["ema_9"] > out["ema_21"]).astype(int)
    out["ema21_above_ema50"] = (out["ema_21"] > out["ema_50"]).astype(int)
    out["ma_slope_20"] = distance_from_ma(out["sma_20"], out["sma_20"].shift(5)) / 5
    out["ma_slope_50"] = distance_from_ma(out["sma_50"], out["sma_50"].shift(10)) / 10
    score = (
        out[["close_above_sma20", "close_above_sma50", "close_above_sma200", "ema9_above_ema21", "ema21_above_ema50"]]
        .mean(axis=1)
        .mul(100)
    )
    out["trend_strength_score"] = score.clip(0, 100).round(2)
    out["trend_short"] = [_state(s, sl) for s, sl in zip(score, out["ma_slope_20"])]
    out["trend_medium"] = [_state(s, sl) for s, sl in zip(score, out["ma_slope_50"])]
    out["trend_long"] = np.where(out["close_above_sma200"].eq(1), "ALTA_TENDENCIAL", "BAIXA_TENDENCIAL")
    out.loc[out["sma_200"].isna(), "trend_long"] = "INDEFINIDO"
    return out


def calculate_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    if "ticker" in work.columns:
        return work.groupby("ticker", group_keys=False).apply(_features_one).reset_index(drop=True)
    return _features_one(work).reset_index(drop=True)

