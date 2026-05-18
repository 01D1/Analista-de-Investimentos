import numpy as np
import pandas as pd

from src.risk.volatility_models import (
    calculate_atr_volatility,
    calculate_close_to_close_vol,
    calculate_ewma_volatility,
    calculate_garman_klass_volatility,
    calculate_parkinson_volatility,
    calculate_volatility_features,
    classify_volatility_regime,
)


def _prices(rows=80):
    close = pd.Series(np.linspace(20, 30, rows) + np.sin(np.arange(rows)), dtype=float)
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=rows).astype(str),
            "ticker": "PETR4",
            "open": close * 0.995,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
        }
    )


def test_historical_and_ewma_volatility_are_positive():
    returns = pd.Series([0.01, -0.02, 0.015, -0.005] * 20)
    assert calculate_close_to_close_vol(returns, 5).dropna().iloc[-1] > 0
    assert calculate_ewma_volatility(returns).iloc[-1] > 0


def test_range_based_volatility_models():
    df = _prices()
    assert calculate_parkinson_volatility(df["high"], df["low"]).dropna().iloc[-1] > 0
    assert calculate_garman_klass_volatility(df["open"], df["high"], df["low"], df["close"]).dropna().iloc[-1] >= 0
    assert calculate_atr_volatility(df["high"], df["low"], df["close"]).dropna().iloc[-1] > 0


def test_volatility_features_and_regime():
    features = calculate_volatility_features(_prices())
    assert {"vol_20d", "vol_60d", "vol_ewma", "ensemble_vol", "volatility_regime"}.issubset(features.columns)
    assert features["ensemble_vol"].notna().any()
    assert classify_volatility_regime({"ensemble_vol": np.nan}) == "DADOS_INSUFICIENTES"
