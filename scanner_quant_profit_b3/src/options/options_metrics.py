"""Métricas puras para opções."""
from __future__ import annotations

import math
from datetime import date
from typing import Any

import pandas as pd


def _num(value: Any) -> float:
    try:
        if value is None or pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    if math.isnan(value):
        return 0.0
    return round(max(lo, min(hi, value)), 4)


def calculate_moneyness(option_type: str, underlying_price: float, strike: float) -> tuple[float, str]:
    S = _num(underlying_price)
    K = _num(strike)
    if not (S > 0 and K > 0):
        return float("nan"), "UNKNOWN"
    opt = str(option_type or "").upper()
    if opt == "CALL":
        pct = (S - K) / K * 100
    elif opt == "PUT":
        pct = (K - S) / K * 100
    else:
        return float("nan"), "UNKNOWN"
    abs_pct = abs(pct)
    if abs_pct <= 2:
        klass = "ATM"
    elif pct > 15:
        klass = "DEEP_ITM"
    elif pct > 2:
        klass = "ITM"
    elif pct < -15:
        klass = "DEEP_OTM"
    else:
        klass = "OTM"
    return round(pct, 4), klass


def calculate_intrinsic_value(option_type: str, underlying_price: float, strike: float) -> float:
    S = _num(underlying_price)
    K = _num(strike)
    if not (S >= 0 and K >= 0):
        return float("nan")
    opt = str(option_type or "").upper()
    if opt == "CALL":
        return round(max(S - K, 0.0), 6)
    if opt == "PUT":
        return round(max(K - S, 0.0), 6)
    return float("nan")


def calculate_extrinsic_value(option_price: float, intrinsic_value: float) -> float:
    price = _num(option_price)
    intrinsic = _num(intrinsic_value)
    if math.isnan(price) or math.isnan(intrinsic):
        return float("nan")
    return round(max(price - intrinsic, 0.0), 6)


def calculate_breakeven(option_type: str, strike: float, option_price: float) -> float:
    K = _num(strike)
    price = _num(option_price)
    if math.isnan(K) or math.isnan(price):
        return float("nan")
    opt = str(option_type or "").upper()
    if opt == "CALL":
        return round(K + price, 6)
    if opt == "PUT":
        return round(K - price, 6)
    return float("nan")


def calculate_spread_metrics(bid: float, ask: float, last_price: float) -> tuple[float, float]:
    b = _num(bid)
    a = _num(ask)
    last = _num(last_price)
    if not (a >= 0 and b >= 0) or a < b:
        return float("nan"), float("nan")
    spread = a - b
    ref = ((a + b) / 2) if (a + b) > 0 else last
    pct = (spread / ref * 100) if ref and ref > 0 else float("nan")
    return round(spread, 6), round(pct, 6) if not math.isnan(pct) else float("nan")


def calculate_days_to_maturity(maturity_date: Any, reference_date: Any | None = None) -> int | None:
    m = pd.to_datetime(maturity_date, errors="coerce")
    r = pd.to_datetime(reference_date or date.today(), errors="coerce")
    if pd.isna(m) or pd.isna(r):
        return None
    return int((m.date() - r.date()).days)


def calculate_option_liquidity_score(volume: float, trades: float, financial_volume: float, spread_pct: float, open_interest: float | None = None) -> float:
    vol = max(_num(volume), 0.0)
    neg = max(_num(trades), 0.0)
    fin = max(_num(financial_volume), 0.0)
    spread = _num(spread_pct)
    oi = max(_num(open_interest), 0.0) if open_interest is not None else 0.0
    score = 0.0
    score += min(fin / 1_000_000, 1.0) * 35
    score += min(neg / 500, 1.0) * 25
    score += min(vol / 100_000, 1.0) * 20
    if not math.isnan(spread):
        score += max(0.0, 1 - min(spread, 50) / 50) * 15
    score += min(oi / 50_000, 1.0) * 5
    return _clip(score)


def calculate_option_risk_score(days_to_maturity: int | None, spread_pct: float, theta: float | None = None, liquidity_score: float | None = None, moneyness_class: str | None = None) -> float:
    dte = days_to_maturity if days_to_maturity is not None else -1
    spread = _num(spread_pct)
    liq = _num(liquidity_score)
    theta_v = abs(_num(theta)) if theta is not None else 0.0
    score = 100.0
    if dte < 0:
        score -= 40
    elif dte < 7:
        score -= 35
    elif dte < 15:
        score -= 15
    if not math.isnan(spread):
        score -= min(spread, 60) * 0.8
    if not math.isnan(liq):
        score -= max(0, 50 - liq) * 0.7
    score -= min(theta_v * 100, 20)
    if str(moneyness_class or "").upper() in {"DEEP_OTM", "UNKNOWN"}:
        score -= 10
    return _clip(score)
