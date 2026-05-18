import pandas as pd

from src.paper.performance import calculate_paper_performance, summarize_positions, summarize_trades


def test_paper_performance_metrics():
    equity = pd.DataFrame({"trade_date": ["2026-01-01", "2026-01-02"], "equity": [100_000, 101_000], "daily_return": [0, 0.01], "drawdown": [0, 0], "exposure": [0, 10_000], "portfolio_var_95": [0, 100], "portfolio_es_95": [0, 120]})
    orders = pd.DataFrame({"order_status": ["SIMULATED_FILLED"], "metadata_trade_pnl": [100]})
    summary = calculate_paper_performance(equity, orders)
    assert summary["total_return"] > 0
    assert summary["win_rate"] == 1


def test_summarize_trades_and_positions():
    assert summarize_trades(pd.DataFrame({"order_status": ["SIMULATED_FILLED", "BLOCKED_RISK"]}))["filled_count"] == 1
    assert summarize_positions(pd.DataFrame({"trade_date": ["2026-01-01"], "ticker": ["PETR4"], "quantity": [1], "market_value": [20]}))["positions_count"] == 1

