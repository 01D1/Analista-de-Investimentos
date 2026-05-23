import pandas as pd

from src.scanners import fine_cost_diagnostics


def test_fine_cost_diagnostics_cli_run(monkeypatch, tmp_path):
    orders = pd.DataFrame(
        [
            {"id": 1, "trade_date": "2026-01-02", "ticker": "PETR4", "side": "BUY", "execution_cost": 1, "slippage_cost": 1, "signal_source": "quant", "metadata_json": '{"parent_signal_id":"s1"}'},
            {"id": 2, "trade_date": "2026-01-03", "ticker": "PETR4", "side": "CLOSE", "execution_cost": 2, "slippage_cost": 1, "signal_source": "quant", "metadata_json": '{"exit_rule_triggered":"SIMULATION_END","is_simulation_end_close":true,"metadata_trade_pnl":5}'},
        ]
    )
    monkeypatch.setattr(fine_cost_diagnostics, "load_paper_orders", lambda db, run_id=None: orders)
    monkeypatch.setattr(fine_cost_diagnostics, "load_paper_positions", lambda db, run_id=None: pd.DataFrame())
    monkeypatch.setattr(fine_cost_diagnostics, "load_paper_exit_events", lambda db, run_id=None: pd.DataFrame())
    monkeypatch.setattr(fine_cost_diagnostics, "load_paper_rebalance_events", lambda db, run_id=None: pd.DataFrame())

    result = fine_cost_diagnostics.run(2, save_db=False, csv=False, db_path=tmp_path / "x.db")

    assert result["status"] == "SUCCESS"
    assert result["lifecycle_summary"]["entry_cost_pct"] > 0
    assert not result["exit_rules"].empty
