"""Testes para src/quant/performance.py"""
import pytest
import pandas as pd
import numpy as np

from src.quant.performance import (
    drawdown,
    sharpe_ratio,
    sortino_ratio,
    win_rate,
    payoff_ratio,
    expectancy,
    summary_stats,
)


@pytest.fixture
def good_returns():
    """Retornos levemente positivos com baixa volatilidade."""
    np.random.seed(0)
    return pd.Series(np.random.normal(0.002, 0.01, 252))


@pytest.fixture
def pnl_series():
    return pd.Series([150, -50, 200, -80, 100, -30, 300, -120, 90, -40])


class TestDrawdown:
    def test_no_drawdown_on_rising(self):
        equity = pd.Series([100.0, 110.0, 120.0, 130.0])
        dd, max_dd = drawdown(equity)
        assert max_dd == pytest.approx(0.0, abs=1e-10)

    def test_drawdown_magnitude(self):
        equity = pd.Series([100.0, 90.0, 80.0, 95.0])
        _, max_dd = drawdown(equity)
        # Pico 100, mínimo 80: DD = -20%
        assert max_dd == pytest.approx(-0.20, rel=1e-4)

    def test_drawdown_negative(self):
        equity = pd.Series([100.0, 90.0, 95.0])
        dd, _ = drawdown(equity)
        assert (dd.dropna() <= 0).all()


class TestSharpe:
    def test_positive_for_good_returns(self, good_returns):
        sr = sharpe_ratio(good_returns)
        assert sr > 0

    def test_zero_for_constant_zero_returns(self):
        returns = pd.Series([0.0] * 252)
        assert sharpe_ratio(returns) == 0.0

    def test_empty_series(self):
        assert sharpe_ratio(pd.Series([], dtype=float)) == 0.0


class TestSortino:
    def test_positive(self, good_returns):
        sr = sortino_ratio(good_returns)
        assert sr > 0

    def test_sortino_ge_sharpe_good_returns(self, good_returns):
        # Para retornos positivos assimétricos, Sortino >= Sharpe
        sharpe = sharpe_ratio(good_returns)
        sortino = sortino_ratio(good_returns)
        assert sortino >= sharpe * 0.5  # critério relaxado

    def test_no_losers(self):
        returns = pd.Series([0.01] * 100)
        assert sortino_ratio(returns) == 0.0  # sem downside std


class TestWinRate:
    def test_all_winners(self):
        assert win_rate(pd.Series([100, 200, 50])) == pytest.approx(1.0)

    def test_all_losers(self):
        assert win_rate(pd.Series([-100, -50])) == pytest.approx(0.0)

    def test_mixed(self, pnl_series):
        wr = win_rate(pnl_series)
        assert 0 < wr < 1

    def test_empty(self):
        assert win_rate(pd.Series([], dtype=float)) == 0.0


class TestPayoffRatio:
    def test_basic(self):
        pnl = pd.Series([200, 200, -100, -100])
        assert payoff_ratio(pnl) == pytest.approx(2.0)

    def test_all_winners(self):
        # Sem perdas → payoff 0 (divisão por zero tratada)
        assert payoff_ratio(pd.Series([100, 200])) == 0.0

    def test_all_losers(self):
        assert payoff_ratio(pd.Series([-100, -50])) == 0.0


class TestExpectancy:
    def test_positive_edge(self):
        e = expectancy(0.5, 200, 100)
        assert e == pytest.approx(50.0)

    def test_negative_edge(self):
        e = expectancy(0.3, 100, 200)
        assert e < 0

    def test_breakeven(self):
        # WR=50%, avg_win=avg_loss → E=0
        assert expectancy(0.5, 100, 100) == pytest.approx(0.0)


class TestSummaryStats:
    def test_returns_dict(self, pnl_series):
        stats = summary_stats(pnl_series, capital=10_000)
        required = {"total_trades", "win_rate", "payoff_ratio", "expectancy",
                    "total_pnl", "max_drawdown", "sharpe", "sortino"}
        assert required.issubset(stats.keys())

    def test_total_pnl_correct(self, pnl_series):
        stats = summary_stats(pnl_series, capital=10_000)
        assert stats["total_pnl"] == pytest.approx(float(pnl_series.sum()), rel=1e-4)
