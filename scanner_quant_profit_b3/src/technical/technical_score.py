"""Score tecnico paralelo, opcional e independente do score principal."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _num(df: pd.DataFrame, col: str, default: float = 50) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype="float")
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


def _status(row: pd.Series) -> str:
    if row.get("data_quality_flag") == "DADOS_INSUFICIENTES":
        return "DADOS_INSUFICIENTES"
    if row.get("risk_score", 50) < 30:
        return "TECNICO_RISCO_ELEVADO"
    score = row.get("technical_score_final", 0)
    if score >= 80:
        return "TECNICO_FORTE"
    if score >= 65:
        return "TECNICO_PROMISSOR"
    if score >= 45:
        return "TECNICO_NEUTRO"
    return "TECNICO_FRACO"


def calculate_technical_score(features_df: pd.DataFrame) -> pd.DataFrame:
    if features_df.empty:
        return features_df.copy()
    out = features_df.copy()
    out["trend_score"] = _num(out, "trend_strength_score")
    out["momentum_score"] = _num(out, "momentum_score")
    out["volatility_score"] = _num(out, "volatility_score")
    out["volume_score"] = _num(out, "volume_score")
    out["breakout_score"] = np.select(
        [out.get("breakout_20", False).astype(bool), out.get("breakdown_20", False).astype(bool)],
        [80, 20],
        default=50,
    )
    sr_cols = [c for c in ["near_support_20", "near_resistance_20"] if c in out.columns]
    out["support_resistance_score"] = 50
    if "near_support_20" in sr_cols:
        out.loc[out["near_support_20"].astype(bool), "support_resistance_score"] = 65
    if "near_resistance_20" in sr_cols:
        out.loc[out["near_resistance_20"].astype(bool), "support_resistance_score"] = 45
    pattern_cols = [c for c in ["strength_candle", "reversal_candle", "wide_range_bar"] if c in out.columns]
    out["pattern_score"] = 50
    if pattern_cols:
        out["pattern_score"] = 50 + out[pattern_cols].astype(bool).sum(axis=1).clip(0, 3) * 10
    high_vol_penalty = _num(out, "volatility_zscore", 0).clip(lower=0) * 15
    low_liq_penalty = (1 - (_num(out, "relative_volume_20", 1).clip(0, 1))) * 20
    out["risk_score"] = (80 - high_vol_penalty - low_liq_penalty).clip(0, 100).round(2)
    out["data_quality_flag"] = np.where(out[["close"]].isna().any(axis=1), "DADOS_INSUFICIENTES", "OK")
    weighted = (
        out["trend_score"] * 0.22
        + out["momentum_score"] * 0.20
        + out["volatility_score"] * 0.12
        + out["volume_score"] * 0.14
        + out["breakout_score"] * 0.12
        + out["support_resistance_score"] * 0.08
        + out["pattern_score"] * 0.07
        + out["risk_score"] * 0.05
    )
    out["technical_score_final"] = weighted.clip(0, 100).round(2)
    out["technical_status"] = out.apply(_status, axis=1)
    return out

