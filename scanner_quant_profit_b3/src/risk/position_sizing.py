"""Sizing analitico para estudo de risco."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from src.risk.var_models import calculate_parametric_var


def _shares(value: float, price: float) -> float:
    if price is None or price <= 0 or pd.isna(price):
        return np.nan
    return math.floor(max(value, 0) / price)


def size_by_fixed_risk(capital, risk_pct, entry_price, stop_price):
    risk_amount = float(capital) * float(risk_pct)
    per_share = abs(float(entry_price) - float(stop_price)) if stop_price is not None else np.nan
    if not per_share or pd.isna(per_share) or per_share <= 0:
        return np.nan
    return math.floor(risk_amount / per_share)


def size_by_atr(capital, risk_pct, price, atr, atr_multiplier: float = 2):
    risk_amount = float(capital) * float(risk_pct)
    per_share = float(atr or 0) * atr_multiplier
    if per_share <= 0:
        return np.nan
    return math.floor(risk_amount / per_share)


def size_by_var(capital, var_limit_pct, volatility, confidence: float = 0.95):
    limit = float(capital) * float(var_limit_pct)
    unit_var = calculate_parametric_var(1.0, volatility, confidence)["parametric_var"]
    if pd.isna(unit_var) or unit_var <= 0:
        return np.nan
    return math.floor(limit / unit_var)


def size_by_liquidity(avg_financial_volume, participation_rate: float = 0.01):
    if avg_financial_volume is None or pd.isna(avg_financial_volume) or float(avg_financial_volume) <= 0:
        return np.nan
    return float(avg_financial_volume) * float(participation_rate)


def calculate_final_position_size(capital, risk_pct, entry_price, stop_price=None, atr=None, volatility=None, avg_financial_volume=None, var_limit_pct=0.01, participation_rate=0.01, confidence=0.95) -> dict:
    price = float(entry_price or 0)
    risk_amount = float(capital) * float(risk_pct)
    size_fixed = size_by_fixed_risk(capital, risk_pct, price, stop_price) if stop_price is not None else np.nan
    size_atr = size_by_atr(capital, risk_pct, price, atr) if atr is not None else np.nan
    value_var = size_by_var(capital, var_limit_pct, volatility, confidence) if volatility is not None else np.nan
    size_var = _shares(value_var, price) if pd.notna(value_var) else np.nan
    liq_value = size_by_liquidity(avg_financial_volume, participation_rate)
    size_liq = _shares(liq_value, price) if pd.notna(liq_value) else np.nan
    cap_size = _shares(float(capital), price)
    candidates = {
        "FIXED_RISK": size_fixed,
        "ATR": size_atr,
        "VAR": size_var,
        "LIQUIDITY": size_liq,
        "CAPITAL": cap_size,
    }
    valid = {k: float(v) for k, v in candidates.items() if pd.notna(v) and float(v) >= 0}
    if not valid:
        final_size = 0
        limiting = "DATA_INSUFFICIENT"
    else:
        limiting, final_size = min(valid.items(), key=lambda kv: kv[1])
    final_value = final_size * price
    estimated_var = calculate_parametric_var(final_value, volatility, confidence)["parametric_var"] if volatility is not None else np.nan
    return {
        "size_fixed_risk": size_fixed,
        "size_atr": size_atr,
        "size_var": size_var,
        "size_liquidity": size_liq,
        "final_size": final_size,
        "final_position_value": final_value,
        "limiting_factor": limiting,
        "risk_amount": risk_amount,
        "estimated_var": estimated_var,
        "notes": "Sizing sugerido para estudo; não é aplicação automática.",
    }

