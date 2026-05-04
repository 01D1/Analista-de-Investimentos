"""Testes para src/strategies/call_continuity_strategy.py"""
import sqlite3
import pytest
import pandas as pd
import numpy as np

from src.strategies.call_continuity_strategy import (
    analyze_stock,
    score_and_classify,
    SETUP_STATUS_LABELS,
)


@pytest.fixture
def sample_history():
    """Histórico sintético de 40 dias em tendência de alta."""
    np.random.seed(7)
    base = 35.0
    dates = pd.date_range("2026-01-01", periods=40, freq="B")
    closes = base + np.cumsum(np.random.normal(0.1, 0.5, 40))
    highs = closes * 1.01
    lows = closes * 0.99
    opens = closes * (1 + np.random.normal(0, 0.003, 40))
    volumes = np.random.uniform(50e6, 200e6, 40)
    trades = np.random.randint(5000, 20000, 40)
    return pd.DataFrame({
        "trade_date": dates.strftime("%Y-%m-%d"),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "trades": trades,
    })


@pytest.fixture
def qcfg():
    return {
        "capital_inicial": 10_000,
        "risco_por_trade": 0.005,
        "stop_opcao_pct": 0.30,
        "alvo_1_pct": 0.50,
        "alvo_2_pct": 1.00,
        "min_volume_opcao": 10_000,
        "min_negocios_opcao": 5,
        "min_dte": 15,
        "max_dte": 45,
        "taxa_livre_risco": 0.1475,
        "win_rate_estimado": 0.45,
        "contract_size": 100,
        "sma_fast": 9,
        "sma_slow": 21,
        "rsi_period": 14,
        "atr_period": 14,
        "hv_window": 21,
        "volume_avg_window": 20,
        "score_entrada_validada": 70,
        "score_aguardar": 50,
        "score_weights": {
            "stock_trend_score": 0.25,
            "stock_momentum_score": 0.20,
            "stock_volume_score": 0.15,
            "option_liquidity_score": 0.20,
            "option_moneyness_score": 0.10,
            "option_dte_score": 0.10,
        },
    }


class TestAnalyzeStock:
    def test_valid_returns_dict(self, sample_history, qcfg):
        result = analyze_stock(sample_history, qcfg)
        assert result.get("valid") is True

    def test_has_required_keys(self, sample_history, qcfg):
        result = analyze_stock(sample_history, qcfg)
        required = {"close", "trend", "rsi", "volume_condition", "hist_vol"}
        assert required.issubset(result.keys())

    def test_insufficient_history(self, qcfg):
        short = pd.DataFrame({
            "trade_date": ["2026-01-01", "2026-01-02"],
            "open": [10.0, 10.0],
            "high": [11.0, 11.0],
            "low": [9.0, 9.0],
            "close": [10.0, 10.5],
            "volume": [1e6, 1e6],
            "trades": [1000, 1000],
        })
        result = analyze_stock(short, qcfg)
        assert result.get("valid") is False

    def test_trend_valid_string(self, sample_history, qcfg):
        result = analyze_stock(sample_history, qcfg)
        valid_trends = {"ALTA", "ALTA_PARCIAL", "LATERAL", "QUEDA", "INDEFINIDA"}
        assert result.get("trend") in valid_trends


class TestScoreAndClassify:
    @pytest.fixture
    def stock_up(self, sample_history, qcfg):
        return analyze_stock(sample_history, qcfg)

    @pytest.fixture
    def good_option(self):
        return pd.Series({
            "ticker": "PETRF350",
            "underlying": "PETR4",
            "option_type": "CALL",
            "trade_date": "2026-05-01",
            "expiration_date": "2026-06-20",
            "close": 2.0,
            "strike": 35.0,
            "dte": 30,
            "trades": 100,
            "volume": 500_000,
            "quantity": 10_000,
        })

    def test_returns_dict(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert result is not None
        assert isinstance(result, dict)

    def test_has_status(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert result["status"] in SETUP_STATUS_LABELS

    def test_final_score_range(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert 0 <= result["final_score"] <= 100

    def test_sizing_keys(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert "contratos" in result
        assert "stop" in result
        assert "alvo_1" in result
        assert "alvo_2" in result
        assert "risco_financeiro" in result

    def test_stop_below_entry(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert result["stop"] < result["entrada_planejada"]

    def test_alvo1_above_entry(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert result["alvo_1"] > result["entrada_planejada"]

    def test_alvo2_above_alvo1(self, good_option, stock_up, qcfg):
        result = score_and_classify(good_option, stock_up, qcfg)
        assert result["alvo_2"] > result["alvo_1"]

    def test_invalid_entry_returns_none(self, stock_up, qcfg):
        bad_option = pd.Series({
            "ticker": "XYZF100",
            "underlying": "PETR4",
            "option_type": "CALL",
            "trade_date": "2026-05-01",
            "expiration_date": "2026-06-20",
            "close": 0.0,  # preço inválido
            "strike": 35.0,
            "dte": 30,
            "trades": 100,
            "volume": 500_000,
            "quantity": 10_000,
        })
        result = score_and_classify(bad_option, stock_up, qcfg)
        assert result is None


class TestSetupStatusLabels:
    def test_all_statuses_have_labels(self):
        expected = {"ENTRADA_VALIDADA", "AGUARDAR_GATILHO", "INVALIDADO",
                    "EM_ABERTO", "ALVO_1", "ALVO_2", "STOPADO"}
        assert expected == set(SETUP_STATUS_LABELS.keys())
