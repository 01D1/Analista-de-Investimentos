import json

import pandas as pd

from src.paper.fragility_by_signal_source import analyze_pnl_by_signal_source


def test_signal_source_fragility():
    orders = pd.DataFrame({"signal_source": ["quant", "quant"], "order_status": ["SIMULATED_FILLED", "SIMULATED_FILLED"], "execution_cost": [1, 1], "slippage_cost": [1, 1], "metadata_json": [json.dumps({"metadata_trade_pnl": 5}), json.dumps({"metadata_trade_pnl": -10})]})
    out = analyze_pnl_by_signal_source(orders)
    assert not out.empty
    assert out.iloc[0]["signal_source"] == "quant"
