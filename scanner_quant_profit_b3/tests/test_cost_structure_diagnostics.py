import json

import pandas as pd

from src.paper.cost_structure_diagnostics import analyze_cost_structure


def test_analyze_cost_structure_decomposes_costs():
    orders = pd.DataFrame(
        {
            "trade_date": ["2026-01-01", "2026-01-02"],
            "ticker": ["PETR4", "VALE3"],
            "execution_cost": [2.0, 3.0],
            "slippage_cost": [1.0, 1.0],
            "signal_source": ["quant", "technical"],
            "metadata_json": [json.dumps({"metadata_trade_pnl": 10, "exit_reason": "STOP"}), json.dumps({"metadata_trade_pnl": -2, "primary_regime": "LATERAL"})],
        }
    )
    result = analyze_cost_structure(orders)
    assert result["summary"]["total_cost_drag"] == 7.0
    assert not result["cost_by_ticker"].empty
    assert "cost_drag_class" in result["cost_by_signal_source"].columns

