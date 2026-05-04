"""Testes para src/quant/indicators.py"""
import numpy as np
import pandas as pd
import pytest

from src.quant.indicators import log_returns, sma, ema, atr, rsi, macd, vwap, zscore


@pytest.fixture
def rising_prices():
    return pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0])


@pytest.fixture
def volatile_prices():
    np.random.seed(42)
    base = 100.0
    returns = np.random.normal(0.001, 0.02, 50)
    prices = base * np.exp(np.cumsum(returns))
    return pd.Series(prices)


class TestLogReturns:
    def test_first_is_nan(self, rising_prices):
        result = log_returns(rising_prices)
        assert np.isnan(result.iloc[0])

    def test_positive_for_rising(self, rising_prices):
        result = log_returns(rising_prices).dropna()
        assert (result > 0).all()

    def test_formula(self):
        prices = pd.Series([100.0, 110.0])
        result = log_returns(prices).iloc[1]
        assert result == pytest.approx(np.log(110 / 100), rel=1e-6)


class TestSMA:
    def test_last_value(self, rising_prices):
        result = sma(rising_prices, 3)
        assert result.iloc[-1] == pytest.approx((18.0 + 19.0 + 20.0) / 3)

    def test_length_preserved(self, rising_prices):
        result = sma(rising_prices, 5)
        assert len(result) == len(rising_prices)

    def test_single_value(self):
        prices = pd.Series([42.0])
        result = sma(prices, 10)
        assert result.iloc[0] == pytest.approx(42.0)


class TestEMA:
    def test_length_preserved(self, volatile_prices):
        result = ema(volatile_prices, 9)
        assert len(result) == len(volatile_prices)

    def test_ema_tracks_trend(self, rising_prices):
        fast = ema(rising_prices, 3)
        slow = ema(rising_prices, 9)
        # Em tendência de alta, a EMA rápida deve estar acima da lenta no final
        assert float(fast.iloc[-1]) >= float(slow.iloc[-1])


class TestATR:
    def test_positive(self, volatile_prices):
        high = volatile_prices * 1.01
        low = volatile_prices * 0.99
        result = atr(high, low, volatile_prices)
        assert (result.dropna() > 0).all()

    def test_length_preserved(self, volatile_prices):
        high = volatile_prices * 1.01
        low = volatile_prices * 0.99
        result = atr(high, low, volatile_prices)
        assert len(result) == len(volatile_prices)


class TestRSI:
    def test_bounds(self, volatile_prices):
        result = rsi(volatile_prices, 14).dropna()
        assert (result >= 0).all()
        assert (result <= 100).all()

    def test_rising_high_rsi(self, rising_prices):
        result = rsi(rising_prices, 5).dropna()
        # Série puramente crescente → RSI alto
        assert float(result.iloc[-1]) > 60

    def test_length_preserved(self, volatile_prices):
        result = rsi(volatile_prices, 14)
        assert len(result) == len(volatile_prices)


class TestMACD:
    def test_returns_three_series(self, volatile_prices):
        macd_line, signal_line, hist = macd(volatile_prices)
        assert len(macd_line) == len(volatile_prices)
        assert len(signal_line) == len(volatile_prices)
        assert len(hist) == len(volatile_prices)

    def test_histogram_is_difference(self, volatile_prices):
        macd_line, signal_line, hist = macd(volatile_prices)
        diff = (macd_line - signal_line).dropna()
        h = hist.dropna()
        # Os elementos onde ambos têm valores devem ser iguais
        common_idx = diff.index.intersection(h.index)
        np.testing.assert_allclose(
            diff.loc[common_idx].values,
            h.loc[common_idx].values,
            rtol=1e-6,
        )


class TestVWAP:
    def test_constant_price(self):
        prices = pd.Series([50.0] * 10)
        volumes = pd.Series([1000.0] * 10)
        result = vwap(prices, volumes)
        np.testing.assert_allclose(result.dropna().values, 50.0, rtol=1e-5)

    def test_length_preserved(self, volatile_prices):
        volumes = pd.Series(np.random.uniform(1e5, 1e6, len(volatile_prices)))
        result = vwap(volatile_prices, volumes)
        assert len(result) == len(volatile_prices)


class TestZScore:
    def test_zero_for_constant(self):
        prices = pd.Series([10.0] * 30)
        result = zscore(prices, 20)
        # Std = 0 → NaN (divisão por zero tratada)
        assert result.dropna().empty or (result.dropna() == 0).all()

    def test_recent_outlier(self):
        base = pd.Series([10.0] * 25)
        spike = pd.concat([base, pd.Series([100.0])], ignore_index=True)
        result = zscore(spike, 20)
        # O último valor (outlier) deve ter Z muito alto
        assert float(result.iloc[-1]) > 3
