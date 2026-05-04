"""Testes para src/quant/risk_models.py e src/quant/position_sizing.py"""
import pytest
import pandas as pd
import numpy as np

from src.quant.risk_models import (
    value_at_risk,
    kelly_fraction,
    risk_amount,
    position_size,
    financial_risk,
    stop_price,
    target_price,
)
from src.quant.position_sizing import compute_sizing


class TestVaR:
    @pytest.fixture
    def returns(self):
        np.random.seed(1)
        return pd.Series(np.random.normal(0.001, 0.02, 252))

    def test_var_positive(self, returns):
        var = value_at_risk(returns, confidence=0.95)
        assert var > 0

    def test_var_99_greater_than_95(self, returns):
        var95 = value_at_risk(returns, 0.95)
        var99 = value_at_risk(returns, 0.99)
        assert var99 >= var95

    def test_empty_series(self):
        assert value_at_risk(pd.Series([], dtype=float)) == 0.0


class TestKelly:
    def test_positive_edge(self):
        # WR=60%, payoff=2x → Kelly positivo
        k = kelly_fraction(0.60, 2.0, fraction=1.0)
        assert k > 0

    def test_zero_edge(self):
        # WR=33%, payoff=2x → Kelly = (0.33*2 - 0.67)/2 = -0.005 → clamp 0
        k = kelly_fraction(0.33, 2.0, fraction=1.0)
        assert k >= 0

    def test_conservative_fraction(self):
        k_full = kelly_fraction(0.60, 2.0, fraction=1.0)
        k_quarter = kelly_fraction(0.60, 2.0, fraction=0.25)
        assert k_quarter == pytest.approx(k_full * 0.25, rel=1e-4)

    def test_zero_payoff(self):
        assert kelly_fraction(0.60, 0.0) == 0.0


class TestRiskAmount:
    def test_basic(self):
        assert risk_amount(10_000, 0.005) == pytest.approx(50.0)


class TestPositionSize:
    def test_basic(self):
        # R$ 50 de risco / R$ 0.60 por contrato (entrada 2.0, stop 1.4, size 100)
        # contratos = 50 / ((2.0 - 1.4) * 100) = 50 / 60 ≈ 0 → 0 contratos
        size = position_size(10_000, 0.005, 2.0, 1.4, contract_size=100)
        assert size == 0

    def test_larger_capital(self):
        # R$ 1000 de risco / R$ 60 = 16 contratos
        size = position_size(200_000, 0.005, 2.0, 1.4, contract_size=100)
        assert size == 16

    def test_invalid_stop(self):
        assert position_size(10_000, 0.005, 2.0, 2.0) == 0
        assert position_size(10_000, 0.005, 2.0, 3.0) == 0

    def test_zero_entry(self):
        assert position_size(10_000, 0.005, 0.0, 0.0) == 0


class TestStopTarget:
    def test_stop_below_entry(self):
        s = stop_price(2.0, 0.30)
        assert s == pytest.approx(2.0 * 0.70, rel=1e-6)

    def test_target_above_entry(self):
        t = target_price(2.0, 0.50)
        assert t == pytest.approx(3.0, rel=1e-6)


class TestComputeSizing:
    def test_returns_dict(self):
        result = compute_sizing(
            capital=10_000,
            risk_pct=0.005,
            entry=2.50,
            stop_pct=0.30,
            target1_pct=0.50,
            target2_pct=1.00,
        )
        required_keys = {"contracts", "entry", "stop", "alvo_1", "alvo_2",
                         "risco_financeiro", "payoff_ratio", "kelly_fraction"}
        assert required_keys.issubset(result.keys())

    def test_payoff_ratio(self):
        result = compute_sizing(10_000, 0.005, 2.50, 0.30, 0.50, 1.00)
        # payoff = target1_pct / stop_pct = 0.50 / 0.30 ≈ 1.67 (arredondado a 2 decimais)
        assert result["payoff_ratio"] == pytest.approx(0.50 / 0.30, abs=0.01)

    def test_alvo1_correct(self):
        result = compute_sizing(10_000, 0.005, 2.0, 0.30, 0.50, 1.00)
        assert result["alvo_1"] == pytest.approx(2.0 * 1.50, rel=1e-4)

    def test_alvo2_correct(self):
        result = compute_sizing(10_000, 0.005, 2.0, 0.30, 0.50, 1.00)
        assert result["alvo_2"] == pytest.approx(4.0, rel=1e-4)
