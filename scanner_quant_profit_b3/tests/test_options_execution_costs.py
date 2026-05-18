import math

from src.options.options_execution_costs import (
    calculate_leg_execution_price,
    calculate_structure_execution_costs,
    classify_structure_execution_quality,
)


def test_leg_execution_uses_bid_ask_and_last_fallback():
    leg = {"bid": 1.0, "ask": 1.2, "last_price": 1.1}
    assert calculate_leg_execution_price(leg, "buy")["price"] == 1.2
    assert calculate_leg_execution_price(leg, "sell")["price"] == 1.0
    fallback = calculate_leg_execution_price({"last_price": 2.0}, "buy", slippage_bps=10)
    assert fallback["flag"] == "LAST_FALLBACK"
    assert fallback["price"] > 2.0
    assert math.isnan(calculate_leg_execution_price({}, "buy")["price"])


def test_structure_execution_costs_and_quality():
    legs = [{"direction": "BUY", "bid": 1.0, "ask": 1.1, "last_price": 1.05, "quantity": 1, "spread_pct": 5, "volume": 10000, "trades": 100, "financial_volume": 500000}]
    costs = calculate_structure_execution_costs({"legs": legs}, cost_bps=10, slippage_bps=5)
    assert costs["total_transaction_cost"] > 0
    assert costs["spread_cost"] > 0
    assert classify_structure_execution_quality(legs) in {"BOA", "ACEITAVEL"}

