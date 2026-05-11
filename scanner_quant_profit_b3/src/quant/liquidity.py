"""Métricas e score de liquidez para ações e opções."""
from __future__ import annotations

from typing import Any

import numpy as np

from .metrics import safe_divide, to_float


def _clip_score(value: float) -> float:
    return round(float(np.clip(value, 0.0, 100.0)), 4)


def liquidity_profile(
    *,
    volume: Any,
    trades: Any,
    avg_volume: Any | None = None,
    avg_trades: Any | None = None,
    spread_pct: Any | None = None,
    min_volume: float = 50_000_000,
    min_trades: int = 1_000,
) -> dict:
    volume_f = to_float(volume, default=0.0)
    trades_f = to_float(trades, default=0.0)
    avg_volume_f = to_float(avg_volume, default=np.nan)
    avg_trades_f = to_float(avg_trades, default=np.nan)
    spread_f = to_float(spread_pct, default=np.nan)

    volume_ratio = safe_divide(volume_f, avg_volume_f, default=1.0)
    trades_ratio = safe_divide(trades_f, avg_trades_f, default=1.0)

    absolute_score = min(safe_divide(volume_f, min_volume, default=0.0), 1.0) * 35
    trades_score = min(safe_divide(trades_f, min_trades, default=0.0), 1.0) * 25
    relative_score = min(volume_ratio / 2.0, 1.0) * 25 + min(trades_ratio / 2.0, 1.0) * 15

    penalty = 0.0
    if not np.isnan(spread_f):
        if spread_f > 2.0:
            penalty = 30.0
        elif spread_f > 1.0:
            penalty = 15.0
        elif spread_f > 0.5:
            penalty = 7.0

    score = _clip_score(absolute_score + trades_score + relative_score - penalty)

    return {
        "volume": volume_f,
        "trades": trades_f,
        "volume_ratio": round(volume_ratio, 4),
        "trades_ratio": round(trades_ratio, 4),
        "spread_pct": None if np.isnan(spread_f) else round(spread_f, 4),
        "passes_minimum": bool(volume_f >= min_volume and trades_f >= min_trades),
        "liquidity_score": score,
    }
