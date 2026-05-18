import pandas as pd

from src.options.options_backtest_store import (
    load_option_structure_backtest_results,
    load_option_structure_backtest_runs,
    save_option_structure_backtest_run,
)


def test_save_and_load_option_backtest_run(tmp_path):
    db = tmp_path / "db.sqlite"
    results = pd.DataFrame(
        [
            {
                "entry_date": "2026-01-02",
                "exit_date": "2026-01-07",
                "underlying": "PETR4",
                "structure_type": "LONG_CALL",
                "maturity_date": "2026-02-20",
                "dte_entry": 40,
                "dte_exit": 35,
                "legs_json": "[]",
                "entry_debit": 100,
                "entry_credit": 0,
                "exit_value": 150,
                "gross_pnl": 50,
                "net_pnl": 48,
                "gross_return": 50,
                "net_return": 48,
                "max_loss": 100,
                "return_on_risk": 48,
                "exit_reason": "HOLDING_DAYS",
                "liquidity_score": 80,
                "spread_cost": 1,
                "transaction_cost": 1,
                "slippage_cost": 1,
                "execution_quality": "BOA",
                "status": "COMPLETED",
                "metadata_json": "{}",
            }
        ]
    )
    run_id = save_option_structure_backtest_run(db, {"status": "SUCCESS", "structure_type": "LONG_CALL", "total_trades": 1, "completed_count": 1, "mean_net_return": 48, "win_rate": 100}, results)
    assert run_id == 1
    assert load_option_structure_backtest_runs(db).loc[0, "structure_type"] == "LONG_CALL"
    assert load_option_structure_backtest_results(db, run_id=1).loc[0, "net_return"] == 48

