"""Black-Scholes e Greeks aproximados sem dependência externa."""
from __future__ import annotations

import math


def _valid(S: float, K: float, T: float, sigma: float) -> bool:
    return S is not None and K is not None and T is not None and sigma is not None and S > 0 and K > 0 and T > 0 and sigma > 0


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    if not _valid(S, K, T, sigma):
        return float("nan")
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    opt = str(option_type or "").upper()
    if opt == "CALL":
        return S * _cdf(d1) - K * math.exp(-r * T) * _cdf(d2)
    if opt == "PUT":
        return K * math.exp(-r * T) * _cdf(-d2) - S * _cdf(-d1)
    return float("nan")


def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    if not _valid(S, K, T, sigma):
        return float("nan")
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return _cdf(d1) if str(option_type).upper() == "CALL" else _cdf(d1) - 1


def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if not _valid(S, K, T, sigma):
        return float("nan")
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return _pdf(d1) / (S * sigma * math.sqrt(T))


def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    if not _valid(S, K, T, sigma):
        return float("nan")
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    first = -(S * _pdf(d1) * sigma) / (2 * math.sqrt(T))
    opt = str(option_type or "").upper()
    if opt == "CALL":
        annual = first - r * K * math.exp(-r * T) * _cdf(d2)
    elif opt == "PUT":
        annual = first + r * K * math.exp(-r * T) * _cdf(-d2)
    else:
        return float("nan")
    return annual / 365.0


def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if not _valid(S, K, T, sigma):
        return float("nan")
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return S * _pdf(d1) * math.sqrt(T) / 100.0


def estimate_implied_volatility(market_price: float, S: float, K: float, T: float, r: float, option_type: str) -> float:
    if market_price is None or market_price <= 0 or not _valid(S, K, T, 0.2):
        return float("nan")
    low, high = 0.0001, 5.0
    for _ in range(80):
        mid = (low + high) / 2
        price = black_scholes_price(S, K, T, r, mid, option_type)
        if math.isnan(price):
            return float("nan")
        if price > market_price:
            high = mid
        else:
            low = mid
    return round((low + high) / 2, 6)
