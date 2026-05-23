import pandas as pd

from src.paper.rebalance_cost_diagnostics import analyze_rebalance_costs, suggest_rebalance_diagnostics


def test_analyze_rebalance_costs_groups_by_ticker():
    orders = pd.DataFrame(
        [
            {"ticker": "PETR4", "trade_date": "2026-01-02", "side": "REDUCE", "execution_cost": 10, "slippage_cost": 5, "signal_source": "rebalance", "metadata_json": '{"rebalance_event_id": "r1"}'},
            {"ticker": "VALE3", "trade_date": "2026-01-02", "side": "BUY", "execution_cost": 1, "slippage_cost": 1, "signal_source": "quant", "metadata_json": "{}"},
        ]
    )

    result = analyze_rebalance_costs(orders)

    assert result["summary"]["rebalance_orders_count"] == 1
    assert result["rebalance_cost_by_ticker"].iloc[0]["ticker"] == "PETR4"
    assert suggest_rebalance_diagnostics(result["summary"])
