import pandas as pd

from src.paper.order_model import PaperOrder
from src.paper.portfolio import apply_order, calculate_portfolio_drawdown, calculate_portfolio_var, initialize_portfolio, mark_to_market


def test_apply_order_and_mark_to_market():
    portfolio = initialize_portfolio(100_000)
    order = PaperOrder("1", "2026-01-02", "PETR4", "BUY", 10, 20, simulated_execution_price=20, status="SIMULATED_FILLED")
    portfolio = apply_order(portfolio, order)
    assert "PETR4" in portfolio.positions
    portfolio = mark_to_market(portfolio, pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "close": [21]}), "2026-01-02")
    assert portfolio.positions["PETR4"].unrealized_pnl == 10
    close = PaperOrder("2", "2026-01-03", "PETR4", "CLOSE", 10, 21, simulated_execution_price=21, status="SIMULATED_FILLED")
    portfolio = apply_order(portfolio, close)
    assert "PETR4" not in portfolio.positions


def test_drawdown_and_portfolio_var():
    dd = calculate_portfolio_drawdown([100, 110, 90])
    assert dd.min() < 0
    portfolio = initialize_portfolio(100_000)
    order = PaperOrder("1", "2026-01-02", "PETR4", "BUY", 10, 20, simulated_execution_price=20, status="SIMULATED_FILLED")
    portfolio = apply_order(portfolio, order)
    portfolio = mark_to_market(portfolio, pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "close": [20]}), "2026-01-02")
    result = calculate_portfolio_var(
        portfolio,
        pd.DataFrame({"ticker": ["PETR4"], "trade_date": ["2026-01-02"], "recommended_position_value": [200], "parametric_var_95": [5], "expected_shortfall_95": [8], "risk_status": ["RISK_OK"]}),
    )
    assert result["portfolio_var_95"] == 5

