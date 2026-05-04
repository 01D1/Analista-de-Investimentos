"""Testes para src/quant/options_math.py"""
import numpy as np
import pytest
from datetime import date

from src.quant.options_math import (
    black_scholes,
    days_to_expiration,
    estimated_spread,
    liquidity_score,
)


# Parâmetros de referência: PETR4 sintética, strike 35, 30 dias, vol 35%, SELIC 14.75%
REF = dict(S=35.0, K=35.0, T=30 / 365, r=0.1475, sigma=0.35)


class TestBlackScholes:
    def test_call_price_positive(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert bs.price > 0

    def test_put_price_positive(self):
        bs = black_scholes(**REF, option_type="PUT")
        assert bs.price > 0

    def test_call_delta_between_0_and_1(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert 0 <= bs.delta <= 1

    def test_put_delta_between_minus1_and_0(self):
        bs = black_scholes(**REF, option_type="PUT")
        assert -1 <= bs.delta <= 0

    def test_gamma_positive(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert bs.gamma > 0

    def test_vega_positive(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert bs.vega > 0

    def test_theta_negative(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert bs.theta < 0, "Theta de CALL comprada deve ser negativo (decaimento)"

    def test_put_call_parity(self):
        """C - P = S - K * e^(-rT)"""
        c = black_scholes(**REF, option_type="CALL")
        p = black_scholes(**REF, option_type="PUT")
        S, K, T, r = REF["S"], REF["K"], REF["T"], REF["r"]
        expected = S - K * np.exp(-r * T)
        assert abs((c.price - p.price) - expected) < 0.01

    def test_atm_delta_near_half(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert 0.40 <= bs.delta <= 0.65, "Delta ATM deve estar próximo de 0.5"

    def test_itm_call_high_delta(self):
        bs = black_scholes(S=40.0, K=35.0, T=30 / 365, r=0.1475, sigma=0.35, option_type="CALL")
        assert bs.delta > 0.7, "CALL ITM deve ter delta alto"
        assert bs.moneyness == "ITM"

    def test_otm_call_low_delta(self):
        bs = black_scholes(S=30.0, K=35.0, T=30 / 365, r=0.1475, sigma=0.35, option_type="CALL")
        assert bs.delta < 0.4, "CALL OTM deve ter delta baixo"
        assert bs.moneyness == "OTM"

    def test_expired_option(self):
        bs = black_scholes(S=40.0, K=35.0, T=0, r=0.1475, sigma=0.35, option_type="CALL")
        assert bs.price == pytest.approx(5.0, abs=0.01), "Valor intrínseco na expiração"

    def test_zero_vol_raises_gracefully(self):
        bs = black_scholes(S=35.0, K=35.0, T=30 / 365, r=0.1475, sigma=0.0, option_type="CALL")
        assert bs.price >= 0  # não deve explodir

    def test_time_value_nonnegative(self):
        bs = black_scholes(**REF, option_type="CALL")
        assert bs.time_value >= 0


class TestDaysToExpiration:
    def test_basic(self):
        assert days_to_expiration(date(2026, 5, 1), date(2026, 6, 20)) == 50

    def test_same_day(self):
        d = date(2026, 5, 1)
        assert days_to_expiration(d, d) == 0

    def test_past_expiration(self):
        assert days_to_expiration(date(2026, 6, 1), date(2026, 5, 1)) == 0

    def test_string_input(self):
        assert days_to_expiration("2026-05-01", "2026-06-20") == 50

    def test_none_input(self):
        assert days_to_expiration(None, date(2026, 6, 20)) == 0


class TestLiquidityScore:
    def test_full_score(self):
        score = liquidity_score(100, 500_000, 10, 100_000)
        assert score == pytest.approx(100.0)

    def test_zero_trades(self):
        score = liquidity_score(0, 500_000, 10, 100_000)
        assert score < 100

    def test_zero_volume(self):
        score = liquidity_score(100, 0, 10, 100_000)
        assert score < 100

    def test_both_zero(self):
        score = liquidity_score(0, 0, 10, 100_000)
        assert score == pytest.approx(0.0)


class TestEstimatedSpread:
    def test_zero_price(self):
        assert estimated_spread(0, 1000, 10) == float("inf")

    def test_no_trades(self):
        spread = estimated_spread(2.0, 0, 0)
        assert spread == pytest.approx(0.20, rel=0.01)  # 10% do prêmio

    def test_high_liquidity_lower_spread(self):
        illiquid = estimated_spread(2.0, 10_000, 5)
        liquid = estimated_spread(2.0, 500_000, 250)
        assert liquid <= illiquid
