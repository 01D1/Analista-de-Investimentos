import pandas as pd

from src.paper.order_model import PaperOrder
from src.paper.portfolio import apply_order, initialize_portfolio, mark_to_market
from src.paper.risk_controls import check_max_positions, check_var_limit, evaluate_paper_trade_risk


def test_max_positions_blocks():
    portfolio = initialize_portfolio(100_000)
    order = PaperOrder("1", "2026-01-02", "PETR4", "BUY", 1, 10, simulated_execution_price=10, status="SIMULATED_FILLED")
    portfolio = apply_order(portfolio, order)
    assert check_max_positions(portfolio, 1)["status"] == "PAPER_BLOCKED_MAX_POSITIONS"


def test_var_limit_blocks():
    portfolio = initialize_portfolio(100_000)
    portfolio.var_95 = 10_000
    assert check_var_limit(portfolio, 0.01)["status"] == "PAPER_BLOCKED_VAR"


def test_trade_risk_blocks_risk_engine_status():
    order = PaperOrder("1", "2026-01-02", "PETR4", "BUY", 10, 20)
    risk = pd.DataFrame({"risk_status": ["RISK_BLOCKED_VAR"], "recommended_size": [10]})
    assert evaluate_paper_trade_risk(order, initialize_portfolio(100_000), risk)["status"] == "PAPER_BLOCKED_VAR"

