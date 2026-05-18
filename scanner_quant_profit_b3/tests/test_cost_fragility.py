import json

import pandas as pd

from src.paper.cost_fragility import analyze_cost_drag_by_asset, analyze_cost_drag_by_scenario


def test_cost_drag_by_asset_and_scenario():
    orders = pd.DataFrame({"ticker": ["PETR4"], "execution_cost": [2], "slippage_cost": [1], "metadata_json": [json.dumps({"metadata_trade_pnl": 4})]})
    asset = analyze_cost_drag_by_asset(orders)
    scenario = analyze_cost_drag_by_scenario(pd.DataFrame({"scenario_id": ["S"], "scenario_name": ["S"], "signal_source": ["quant"], "cost_bps": [10], "slippage_bps": [5], "total_return": [0.01]}))
    assert asset.iloc[0]["cost_to_pnl_ratio"] > 0
    assert scenario.iloc[0]["cost_fragility_class"] == "COST_ROBUST"
