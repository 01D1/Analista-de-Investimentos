import pandas as pd
import pytest

from src.risk.portfolio_risk import (
    calculate_asset_risk_contribution,
    calculate_correlation_matrix,
    calculate_covariance_matrix,
    calculate_portfolio_drawdown,
    calculate_portfolio_volatility,
    calculate_risk_concentration,
)


def test_portfolio_risk_metrics():
    returns = pd.DataFrame({"PETR4": [0.01, -0.02, 0.03], "VALE3": [0.02, -0.01, 0.01]})
    cov = calculate_covariance_matrix(returns)
    corr = calculate_correlation_matrix(returns)
    vol = calculate_portfolio_volatility([0.5, 0.5], cov)
    contrib = calculate_asset_risk_contribution([0.5, 0.5], cov)
    assert corr.shape == (2, 2)
    assert vol > 0
    assert len(contrib) == 2


def test_drawdown_and_concentration():
    dd = calculate_portfolio_drawdown([100, 110, 90, 120])
    conc = calculate_risk_concentration([0.7, 0.2, 0.1])
    assert dd["max_drawdown"] < 0
    assert conc["top_concentration"] == pytest.approx(0.7)
