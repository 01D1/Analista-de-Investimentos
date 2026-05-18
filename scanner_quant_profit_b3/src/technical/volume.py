"""Features quantitativas de volume."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.technical.indicators import relative_volume, rolling_zscore, sma


def _one(group: pd.DataFrame) -> pd.DataFrame:
    out = group.sort_values("trade_date").copy()
    volume = pd.to_numeric(out.get("volume"), errors="coerce").fillna(0)
    close = pd.to_numeric(out.get("close"), errors="coerce")
    out["volume_ma_20"] = sma(volume, 20)
    out["volume_ma_60"] = sma(volume, 60)
    out["relative_volume_20"] = relative_volume(volume, 20).fillna(0)
    out["relative_volume_60"] = relative_volume(volume, 60).fillna(0)
    out["volume_zscore"] = rolling_zscore(volume, 20)
    price_up = close.diff().fillna(0) > 0
    out["price_volume_confirmation"] = ((price_up & (out["relative_volume_20"] >= 1.2)) | (~price_up & (out["relative_volume_20"] < 0.8))).astype(int)
    out["accumulation_hint"] = ((close.diff() > 0) & (out["relative_volume_20"] >= 1.3)).astype(int)
    out["distribution_hint"] = ((close.diff() < 0) & (out["relative_volume_20"] >= 1.3)).astype(int)
    out["volume_score"] = (out["relative_volume_20"].clip(0, 2.5) / 2.5 * 100).round(2)
    out["volume_state"] = np.select(
        [
            out["accumulation_hint"].eq(1),
            out["distribution_hint"].eq(1),
            out["relative_volume_20"] >= 1.5,
            out["relative_volume_20"] < 0.7,
        ],
        ["ACUMULACAO_POSSIVEL", "DISTRIBUICAO_POSSIVEL", "VOLUME_FORTE", "VOLUME_FRACO"],
        default="VOLUME_NORMAL",
    )
    return out


def calculate_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    if "ticker" in work.columns:
        return work.groupby("ticker", group_keys=False).apply(_one).reset_index(drop=True)
    return _one(work).reset_index(drop=True)

