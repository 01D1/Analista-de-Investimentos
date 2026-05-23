import json

import pandas as pd

from src.paper.cost_diagnostics_store import load_cost_breakeven, load_cost_diagnostics_by_signal_source, load_cost_diagnostics_by_ticker, load_cost_diagnostics_runs, load_turnover_diagnostics, save_cost_diagnostics_run
from src.reports.cost_slippage_diagnostics_report import generate_cost_slippage_diagnostics_markdown
from src.scanners import cost_slippage_diagnostics


def test_cost_diagnostics_store_and_report(tmp_path):
    db = tmp_path / "cost.db"
    cost_result = {
        "summary": {"total_transaction_cost": 2, "total_slippage_cost": 1, "total_cost_drag": 3, "cost_drag_pct_of_gross_pnl": 0.2, "slippage_pct_of_gross_pnl": 0.1, "avg_cost_per_trade": 2, "avg_slippage_per_trade": 1, "cost_drag_class": "COST_DRAG_ACCEPTABLE"},
        "cost_by_ticker": pd.DataFrame({"ticker": ["PETR4"], "trades_count": [1], "gross_pnl": [10], "transaction_cost": [2], "slippage_cost": [1], "total_cost_drag": [3], "cost_drag_pct": [0.3], "cost_drag_class": ["COST_DRAG_HIGH"], "metadata_json": ["{}"]}),
        "cost_by_signal_source": pd.DataFrame({"signal_source": ["quant"], "trades_count": [1], "gross_pnl": [10], "transaction_cost": [2], "slippage_cost": [1], "total_cost_drag": [3], "cost_drag_pct": [0.3], "cost_drag_class": ["COST_DRAG_HIGH"], "metadata_json": ["{}"]}),
    }
    run_id = save_cost_diagnostics_run(db, 2, cost_result["summary"], cost_result["cost_by_ticker"], cost_result["cost_by_signal_source"], {"trades_per_day": 1, "average_holding_period": 0, "turnover_total": 10, "turnover_daily_avg": 10, "turnover_to_return_ratio": 1, "overtrading_flag": False, "stop_take_turnover_flag": False, "source_turnover_flag": False, "asset_turnover_flag": False, "metadata_json": "{}"}, {"max_cost_bps_supported": 10, "max_slippage_bps_supported": 5, "breakeven_turnover_reduction": 0, "breakeven_trade_return_required": 0, "negative_return_scenario": "NONE", "metadata_json": "{}"})
    assert run_id == 1
    assert load_cost_diagnostics_runs(db).loc[0, "cost_drag_class"] == "COST_DRAG_ACCEPTABLE"
    assert load_cost_diagnostics_by_ticker(db, 1).loc[0, "ticker"] == "PETR4"
    assert load_cost_diagnostics_by_signal_source(db, 1).loc[0, "signal_source"] == "quant"
    assert load_turnover_diagnostics(db, 1).loc[0, "turnover_total"] == 10
    assert load_cost_breakeven(db, 1).loc[0, "max_cost_bps_supported"] == 10
    assert "# Diagnóstico de Custo" in generate_cost_slippage_diagnostics_markdown(cost_result)


def test_cost_slippage_diagnostics_cli_run_with_mocks(tmp_path, monkeypatch):
    orders = pd.DataFrame({"trade_date": ["2026-01-01"], "ticker": ["PETR4"], "quantity": [100], "simulated_execution_price": [10], "execution_cost": [2], "slippage_cost": [1], "signal_source": ["quant"], "metadata_json": [json.dumps({"metadata_trade_pnl": 5})]})
    monkeypatch.setattr(cost_slippage_diagnostics, "load_paper_orders", lambda db, run_id=None: orders)
    monkeypatch.setattr(cost_slippage_diagnostics, "load_paper_positions", lambda db, run_id=None: pd.DataFrame())
    monkeypatch.setattr(cost_slippage_diagnostics, "load_paper_equity_curve", lambda db, run_id=None: pd.DataFrame({"trade_date": ["2026-01-01"], "equity": [100000]}))
    monkeypatch.setattr(cost_slippage_diagnostics, "_load_market_data", lambda db, tickers: pd.DataFrame({"trade_date": ["2026-01-01"], "ticker": ["PETR4"], "volume": [100000], "close": [10]}))
    result = cost_slippage_diagnostics.run(2, db_path=tmp_path / "mock.db")
    assert result["cost_summary"]["total_cost_drag"] == 3
    assert result["breakeven"]["max_cost_bps_supported"] >= 0

