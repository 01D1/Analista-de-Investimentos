import json

import pandas as pd

from src.paper.turnover_diagnostics import analyze_turnover


def test_analyze_turnover_flags_high_turnover_by_source():
    orders = pd.DataFrame(
        {
            "trade_date": ["2026-01-01", "2026-01-01"],
            "ticker": ["PETR4", "PETR4"],
            "quantity": [100, 100],
            "simulated_execution_price": [10, 10],
            "signal_source": ["quant", "quant"],
            "metadata_json": [json.dumps({"metadata_trade_pnl": 1, "exit_rule_triggered": "STOP_LOSS"}), json.dumps({"metadata_trade_pnl": -1, "exit_rule_triggered": "TAKE_PROFIT"})],
        }
    )
    result = analyze_turnover(orders)
    assert result["summary"]["turnover_total"] == 2000
    assert not result["turnover_by_exit_rule"].empty

