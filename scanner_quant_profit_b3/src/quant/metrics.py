"""Métricas quantitativas básicas e robustas para snapshots de mercado."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


def to_float(value: Any, default: float = np.nan) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        value = value.replace("R$", "").replace("%", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_divide(numerator: Any, denominator: Any, default: float = np.nan) -> float:
    num = to_float(numerator)
    den = to_float(denominator)
    if np.isnan(num) or np.isnan(den) or den == 0:
        return default
    return num / den


def pct_change(current: Any, reference: Any, default: float = np.nan, ndigits: int = 4) -> float:
    ratio = safe_divide(current, reference, default=np.nan)
    if np.isnan(ratio):
        return default
    return round((ratio - 1.0) * 100.0, ndigits)


def intraday_metrics(row: Mapping[str, Any]) -> dict:
    last = to_float(row.get("last"))
    open_ = to_float(row.get("open"))
    high = to_float(row.get("high"))
    low = to_float(row.get("low"))
    prev_close = to_float(row.get("prev_close"))

    day_range = high - low if not np.isnan(high) and not np.isnan(low) else np.nan
    position = safe_divide(last - low, day_range, default=np.nan)

    return {
        "last": last,
        "open": open_,
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "variation_pct": to_float(row.get("variation_pct"), default=pct_change(last, prev_close)),
        "range_pct": round(safe_divide(day_range, prev_close, default=np.nan) * 100.0, 4),
        "position_range_pct": round(position * 100.0, 4) if not np.isnan(position) else np.nan,
        "gap_pct": pct_change(open_, prev_close),
        "last_vs_open_pct": pct_change(last, open_),
        "last_vs_prev_close_pct": pct_change(last, prev_close),
    }
