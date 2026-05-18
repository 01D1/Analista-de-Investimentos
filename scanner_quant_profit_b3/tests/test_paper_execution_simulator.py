import pandas as pd

from src.paper.execution_simulator import simulate_execution_from_ohlcv, simulate_limit_order, simulate_market_order
from src.paper.order_model import PaperOrder


def test_market_order_slippage_buy_and_sell():
    buy = simulate_market_order(100, "BUY", slippage_bps=10)
    sell = simulate_market_order(100, "SELL", slippage_bps=10)
    assert buy["simulated_execution_price"] > 100
    assert sell["simulated_execution_price"] < 100


def test_limit_order_fill_rules():
    assert simulate_limit_order(99, 100, "BUY")["execution_status"] == "SIMULATED_FILLED"
    assert simulate_limit_order(101, 100, "BUY")["execution_status"] == "SIMULATED_REJECTED"


def test_execution_from_ohlcv_blocks_liquidity():
    order = PaperOrder("1", "2026-01-02", "PETR4", "BUY", 500, 20)
    result = simulate_execution_from_ohlcv(pd.Series({"close": 20, "volume": 100}), order)
    assert result["execution_status"] == "BLOCKED_LIQUIDITY"

