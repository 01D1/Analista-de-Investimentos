import pandas as pd

from src.paper.hypothesis_deep_oos import run_deep_oos_validation


def _fixtures():
    dates = pd.date_range("2026-01-01", "2026-03-15", freq="D").strftime("%Y-%m-%d")
    prices = pd.DataFrame({"trade_date": list(dates) * 2, "ticker": ["PETR4"] * len(dates) + ["VALE3"] * len(dates), "close": list(range(10, 10 + len(dates))) + list(range(20, 20 + len(dates)))})
    signals = pd.DataFrame({"trade_date": list(dates[35:55]) * 2, "ticker": ["PETR4"] * 20 + ["VALE3"] * 20, "signal_source": ["quant"] * 40, "signal_score": [80] * 40})
    regimes = pd.DataFrame({"trade_date": dates, "primary_regime": ["LATERAL"] * len(dates)})
    return prices, {"quant": signals}, regimes


def test_run_deep_oos_validation_generates_rows():
    prices, signals, regimes = _fixtures()
    out = run_deep_oos_validation(
        {"hypothesis_id": "LIMIT_ASSET_WEIGHT", "hypothesis_type": "LIMIT_ASSET_WEIGHT"},
        signals,
        prices,
        regimes_df=regimes,
        cost_scenarios={"BASE_COST": 10},
        slippage_scenarios={"BASE_SLIPPAGE": 5},
    )
    assert not out.empty
    assert "block_reason" in out.columns
    assert "TODOS" in set(out["ticker"])
