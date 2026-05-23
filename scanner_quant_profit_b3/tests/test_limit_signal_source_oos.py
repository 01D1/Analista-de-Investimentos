import pandas as pd

from src.paper.limit_signal_source_oos import run_limit_signal_source_oos


def test_run_limit_signal_source_oos_returns_rows():
    dates = pd.date_range("2026-01-01", "2026-03-15", freq="D").strftime("%Y-%m-%d")
    prices = pd.DataFrame({"trade_date": dates, "ticker": ["PETR4"] * len(dates), "close": range(10, 10 + len(dates))})
    signals = pd.DataFrame({"trade_date": dates[35:55], "ticker": ["PETR4"] * 20, "signal_source": ["quant"] * 20, "signal_score": [80] * 20})
    variants = pd.DataFrame({"variant_id": ["LIMIT_QUANT_ONLY"], "target_source": ["quant"], "parameters_json": ['{"action":"limit_source","keep_every_n":2}'], "required_confirmations": [0], "cost_limit": [None], "slippage_limit": [None], "regime_filter": [""]})
    out = run_limit_signal_source_oos(variants, {"quant": signals}, prices, cost_scenarios={"BASE_COST": 10}, slippage_scenarios={"BASE_SLIPPAGE": 5})
    assert not out.empty
    assert "mean_cost_drag_delta" in out.columns

