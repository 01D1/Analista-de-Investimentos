import pandas as pd

from src.risk.stress_testing import run_portfolio_stress, run_single_asset_stress


def test_single_asset_stress_returns_scenarios():
    df = run_single_asset_stress(10_000)
    assert len(df) == 4
    assert df["estimated_loss"].max() == 2_000


def test_portfolio_stress_black_swan():
    result = run_portfolio_stress(pd.DataFrame({"position_value": [10_000, 5_000]}), "BLACK_SWAN")
    assert result["estimated_loss"] == 4_500
    assert result["affected_assets"] == 2
