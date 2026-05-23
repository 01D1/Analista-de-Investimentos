import pandas as pd

from src.paper.cost_breakeven import calculate_cost_breakeven


def test_calculate_cost_breakeven_detects_supported_cost():
    df = pd.DataFrame({"scenario_name": ["BASE", "HIGH"], "cost_bps": [10, 30], "slippage_bps": [5, 20], "total_return": [0.01, -0.01], "trades_count": [10, 10]})
    result = calculate_cost_breakeven(df)
    assert result["max_cost_bps_supported"] == 10
    assert result["negative_return_scenario"] == "HIGH"

