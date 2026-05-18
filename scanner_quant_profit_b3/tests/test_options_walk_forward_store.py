import pandas as pd

from src.options.options_walk_forward_store import (
    load_options_context_summary,
    load_options_walk_forward_results,
    load_options_walk_forward_runs,
    save_options_walk_forward_run,
)


def test_save_and_load_options_walk_forward(tmp_path):
    db = tmp_path / "db.sqlite"
    results = pd.DataFrame(
        [
            {
                "window_id": 1,
                "train_start": "2026-01-01",
                "train_end": "2026-01-31",
                "test_start": "2026-02-01",
                "test_end": "2026-02-28",
                "train_trades": 2,
                "test_trades": 2,
                "train_mean_net_return": 1,
                "test_mean_net_return": 1,
                "train_win_rate": 50,
                "test_win_rate": 50,
                "train_profit_factor": 1.2,
                "test_profit_factor": 1.1,
                "avg_cost_drag": 1,
                "skipped_pct": 0,
                "positive_test_window": 1,
                "overfitting_flag": 0,
                "insufficient_data_flag": 0,
                "metadata_json": "{}",
            }
        ]
    )
    context = pd.DataFrame([{"context_type": "dte_bucket", "context_value": "16_30", "trades": 2, "mean_net_return": 1, "win_rate": 50, "profit_factor": 1.1, "avg_cost_drag": 1, "skipped_pct": 0, "metadata_json": "{}"}])
    run_id = save_options_walk_forward_run(db, {"status": "SUCCESS", "structure_type": "LONG_CALL", "windows_count": 1, "governance_status": "OPTIONS_OOS_OBSERVATION_ONLY"}, results, context)
    assert run_id == 1
    assert load_options_walk_forward_runs(db).loc[0, "structure_type"] == "LONG_CALL"
    assert load_options_walk_forward_results(db, run_id=1).loc[0, "window_id"] == 1
    assert load_options_context_summary(db, run_id=1).loc[0, "context_type"] == "dte_bucket"

