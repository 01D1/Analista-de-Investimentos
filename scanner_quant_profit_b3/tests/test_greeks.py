import math

from src.options.greeks import (
    black_scholes_price,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    estimate_implied_volatility,
)


def test_black_scholes_and_greeks_simple_call():
    price = black_scholes_price(100, 100, 30 / 365, 0.10, 0.30, "CALL")
    delta = calculate_delta(100, 100, 30 / 365, 0.10, 0.30, "CALL")
    gamma = calculate_gamma(100, 100, 30 / 365, 0.10, 0.30)
    theta = calculate_theta(100, 100, 30 / 365, 0.10, 0.30, "CALL")
    vega = calculate_vega(100, 100, 30 / 365, 0.10, 0.30)

    assert price > 0
    assert 0 < delta < 1
    assert gamma > 0
    assert theta < 0
    assert vega > 0


def test_implied_volatility_and_missing_data():
    market_price = black_scholes_price(100, 100, 30 / 365, 0.10, 0.30, "CALL")
    iv = estimate_implied_volatility(market_price, 100, 100, 30 / 365, 0.10, "CALL")

    assert abs(iv - 0.30) < 0.01
    assert math.isnan(estimate_implied_volatility(0, 100, 100, 30 / 365, 0.10, "CALL"))
