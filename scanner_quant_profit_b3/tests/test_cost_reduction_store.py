import pandas as pd

from src.paper.cost_reduction_store import load_cost_reduction_results, load_cost_reduction_runs, save_cost_reduction_run


def test_save_and_load_cost_reduction_run(tmp_path):
    db = tmp_path / "scanner_quant.db"
    results = pd.DataFrame(
        [
            {
                "variant_id": "DISABLE_REBALANCE",
                "variant_type": "rebalance",
                "total_return": 0.01,
                "max_drawdown": -0.02,
                "trades_count": 10,
                "cost_drag_total": 100,
                "entry_cost": 10,
                "exit_cost": 40,
                "rebalance_cost": 50,
                "cost_reduction": 20,
                "cost_reduction_pct": 0.2,
                "return_delta": 0,
                "drawdown_delta": 0,
                "turnover_delta": -1,
                "improvement_score": 70,
                "governance_status": "COST_REDUCTION_OBSERVATION_ONLY",
                "metadata_json": "{}",
            }
        ]
    )

    run_id = save_cost_reduction_run(db, 2, results)

    assert run_id == 1
    assert load_cost_reduction_runs(db).iloc[0]["best_variant_id"] == "DISABLE_REBALANCE"
    assert len(load_cost_reduction_results(db, run_id=run_id)) == 1
