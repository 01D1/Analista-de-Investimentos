import pandas as pd

from src.paper.order_model import PaperPosition
from src.paper.rebalancing import calculate_rebalance_orders, calculate_target_weights_by_risk


def test_target_weights_by_risk_zeroes_blocked_assets():
    risk = pd.DataFrame({"ticker": ["PETR4", "VALE3"], "ensemble_vol": [0.2, 0.4], "parametric_var_95": [10, 20], "risk_status": ["RISK_OK", "RISK_BLOCKED_VAR"]})
    weights = calculate_target_weights_by_risk(risk)
    assert weights.loc[weights["ticker"] == "VALE3", "target_weight"].iloc[0] == 0


def test_rebalance_orders_from_target_weights():
    positions = {"PETR4": PaperPosition("PETR4", 10, 20, market_price=20, market_value=200)}
    targets = pd.DataFrame({"ticker": ["PETR4"], "target_weight": [0.1], "reason": ["teste"]})
    prices = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "close": [20]})
    orders = calculate_rebalance_orders(positions, targets, 10_000, prices)
    assert not orders.empty
    assert orders.iloc[0]["side"] == "BUY"

