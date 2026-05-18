import numpy as np
import pandas as pd

from src.risk.expected_shortfall import (
    calculate_historical_expected_shortfall,
    calculate_parametric_expected_shortfall,
)


def test_historical_expected_shortfall_tail_average():
    returns = pd.Series(np.linspace(-0.10, 0.05, 100))
    result = calculate_historical_expected_shortfall(returns, 10_000, confidence=0.95)
    assert result["expected_shortfall"] > 0
    assert result["tail_observations"] > 0


def test_parametric_expected_shortfall_positive():
    result = calculate_parametric_expected_shortfall(10_000, 0.20)
    assert result["expected_shortfall"] > 0


def test_expected_shortfall_insufficient_data():
    result = calculate_historical_expected_shortfall(pd.Series([], dtype=float), 10_000)
    assert np.isnan(result["expected_shortfall"])
