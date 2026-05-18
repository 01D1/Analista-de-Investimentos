import json

import pandas as pd

from src.paper.fragility_by_asset import analyze_pnl_by_asset, generate_asset_fragility_report


def test_analyze_pnl_by_asset():
    orders = pd.DataFrame(
        {
            "ticker": ["PETR4", "PETR4", "VALE3"],
            "order_status": ["SIMULATED_FILLED"] * 3,
            "execution_cost": [1, 1, 2],
            "slippage_cost": [0.5, 0.5, 1],
            "metadata_json": [json.dumps({"metadata_trade_pnl": 10}), json.dumps({"metadata_trade_pnl": -5}), json.dumps({"metadata_trade_pnl": -2})],
        }
    )
    positions = pd.DataFrame({"ticker": ["PETR4"], "unrealized_pnl": [-3]})
    out = analyze_pnl_by_asset(orders, positions)
    assert "fragility_score" in out.columns
    assert "PETR4" in out["ticker"].tolist()
    assert "Fragilidade" in generate_asset_fragility_report(out)
