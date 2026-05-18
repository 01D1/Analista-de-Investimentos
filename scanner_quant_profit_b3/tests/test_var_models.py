import numpy as np
import pandas as pd

from src.risk.var_models import (
    calculate_component_var,
    calculate_historical_var,
    calculate_modified_var,
    calculate_parametric_var,
    calculate_portfolio_var,
)


def test_parametric_var_positive():
    result = calculate_parametric_var(10_000, 0.20, confidence=0.95)
    assert result["parametric_var"] > 0
    assert result["diagnostic_message"] == "OK"


def test_historical_and_modified_var():
    returns = pd.Series(np.linspace(-0.04, 0.03, 80))
    assert calculate_historical_var(returns, 10_000)["historical_var"] > 0
    assert calculate_modified_var(returns, 10_000)["modified_var"] > 0


def test_var_insufficient_data_returns_nan():
    result = calculate_historical_var(pd.Series([0.01]), 10_000)
    assert pd.isna(result["historical_var"])


def test_portfolio_var_and_component_var():
    cov = np.array([[0.0004, 0.0001], [0.0001, 0.0009]])
    weights = [0.6, 0.4]
    result = calculate_portfolio_var(weights, cov, 100_000)
    comp = calculate_component_var(weights, cov, 100_000)
    assert result["portfolio_var"] > 0
    assert len(comp["component_var"]) == 2
