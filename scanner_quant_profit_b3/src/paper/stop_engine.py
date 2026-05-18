"""Stops e alvos para posições simuladas."""
from __future__ import annotations

import pandas as pd


def _num(value, default=None):
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def calculate_fixed_stop(entry_price, stop_loss_pct, side: str = "long"):
    entry = _num(entry_price)
    pct = _num(stop_loss_pct, 0)
    if entry is None or pct <= 0:
        return None
    return entry * (1 - pct) if side.lower() == "long" else entry * (1 + pct)


def calculate_take_profit(entry_price, take_profit_pct, side: str = "long"):
    entry = _num(entry_price)
    pct = _num(take_profit_pct, 0)
    if entry is None or pct <= 0:
        return None
    return entry * (1 + pct) if side.lower() == "long" else entry * (1 - pct)


def calculate_atr_stop(entry_price, atr, atr_multiplier: float = 2, side: str = "long"):
    entry = _num(entry_price)
    atr_value = _num(atr)
    if entry is None or atr_value is None or atr_value <= 0:
        return None
    distance = atr_value * float(atr_multiplier)
    return entry - distance if side.lower() == "long" else entry + distance


def update_trailing_stop(previous_trailing_stop, current_price, trail_pct, side: str = "long"):
    price = _num(current_price)
    pct = _num(trail_pct, 0)
    previous = _num(previous_trailing_stop)
    if price is None or pct <= 0:
        return previous
    candidate = price * (1 - pct) if side.lower() == "long" else price * (1 + pct)
    if previous is None:
        return candidate
    return max(previous, candidate) if side.lower() == "long" else min(previous, candidate)


def check_stop_triggered(low, high, stop_price, side: str = "long") -> dict:
    low_value = _num(low)
    high_value = _num(high)
    stop = _num(stop_price)
    if stop is None or low_value is None or high_value is None:
        return {"triggered": False, "execution_price": None, "reason": "DADOS_INSUFICIENTES"}
    if side.lower() == "long":
        triggered = low_value <= stop
    else:
        triggered = high_value >= stop
    return {"triggered": bool(triggered), "execution_price": stop if triggered else None, "reason": "STOP_TRIGGERED" if triggered else "NO_STOP"}


def check_take_profit_triggered(low, high, target_price, side: str = "long") -> dict:
    low_value = _num(low)
    high_value = _num(high)
    target = _num(target_price)
    if target is None or low_value is None or high_value is None:
        return {"triggered": False, "execution_price": None, "reason": "DADOS_INSUFICIENTES"}
    if side.lower() == "long":
        triggered = high_value >= target
    else:
        triggered = low_value <= target
    return {"triggered": bool(triggered), "execution_price": target if triggered else None, "reason": "TAKE_PROFIT_TRIGGERED" if triggered else "NO_TAKE_PROFIT"}

