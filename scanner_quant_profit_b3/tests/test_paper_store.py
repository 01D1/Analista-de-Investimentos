import pandas as pd

from src.paper.paper_store import (
    load_paper_equity_curve,
    load_paper_exit_events,
    load_paper_orders,
    load_paper_pnl_attribution,
    load_paper_positions,
    load_paper_rebalance_events,
    load_paper_simulation_runs,
    save_paper_simulation_run,
)


def test_paper_store_roundtrip(tmp_path):
    db = tmp_path / "paper.db"
    summary = {"status": "COMPLETED", "capital_initial": 100_000, "capital_final": 101_000, "total_return": 0.01, "sharpe": 1, "sortino": 1, "max_drawdown": 0, "trades_count": 2, "win_rate": 1, "profit_factor": 2, "governance_status": "PAPER_OBSERVATION_ONLY"}
    orders = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "side": ["BUY"], "quantity": [1], "theoretical_price": [20], "simulated_execution_price": [20], "execution_cost": [0], "slippage_cost": [0], "order_status": ["SIMULATED_FILLED"], "signal_source": ["test"], "rejection_reason": [None], "metadata_json": ["{}"]})
    positions = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "quantity": [1], "avg_price": [20], "market_price": [21], "market_value": [21], "unrealized_pnl": [1], "realized_pnl": [0], "var_95": [1], "expected_shortfall_95": [2], "metadata_json": ["{}"]})
    equity = pd.DataFrame({"trade_date": ["2026-01-02"], "cash": [99980], "equity": [100001], "exposure": [21], "daily_return": [0.00001], "drawdown": [0], "portfolio_var_95": [1], "portfolio_es_95": [2], "metadata_json": ["{}"]})
    exits = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "position_id": ["PETR4"], "exit_rule_triggered": ["TAKE_PROFIT_PCT"], "exit_reason": ["teste"], "exit_price": [21], "pnl": [1], "metadata_json": ["{}"]})
    rebalance = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "action": ["REDUCE"], "current_weight": [0.2], "target_weight": [0.1], "order_quantity": [1], "reason": ["teste"], "metadata_json": ["{}"]})
    attribution = pd.DataFrame({"attribution_type": ["signal_source"], "bucket": ["quant"], "trades": [1], "gross_pnl": [1], "net_pnl": [1], "win_rate": [1], "avg_return": [1], "contribution_pct": [1], "metadata_json": ["{}"]})
    run_id = save_paper_simulation_run(db, summary, orders, positions, equity, exits, rebalance, attribution)
    assert run_id == 1
    assert len(load_paper_simulation_runs(db)) == 1
    assert len(load_paper_orders(db, run_id)) == 1
    assert len(load_paper_positions(db, run_id)) == 1
    assert len(load_paper_equity_curve(db, run_id)) == 1
    assert len(load_paper_exit_events(db, run_id)) == 1
    assert len(load_paper_rebalance_events(db, run_id)) == 1
    assert len(load_paper_pnl_attribution(db, run_id)) == 1
