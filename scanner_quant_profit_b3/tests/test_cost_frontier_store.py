import pandas as pd

from src.paper.cost_frontier_store import load_cost_frontier_results, load_cost_frontier_runs, save_cost_frontier_run


def test_save_and_load_cost_frontier_run(tmp_path):
    db = tmp_path / "scanner_quant.db"
    results = pd.DataFrame(
        [
            {
                "variant_id": "A",
                "variant_type": "exit",
                "cost_reduction_pct": 0.2,
                "return_delta": 0.01,
                "drawdown_delta": 0.01,
                "turnover_delta": -1,
                "profit_factor_delta": 0.1,
                "efficiency_score": 90,
                "is_efficient": True,
                "frontier_rank": 1,
                "tradeoff_score": 80,
                "tradeoff_class": "TRADEOFF_STRONG",
                "governance_status": "COST_FRONTIER_APPROVED_FOR_MORE_TESTING",
                "metadata_json": "{}",
            }
        ]
    )

    run_id = save_cost_frontier_run(db, 3, results)

    assert run_id == 1
    assert load_cost_frontier_runs(db).iloc[0]["best_variant_id"] == "A"
    assert len(load_cost_frontier_results(db, run_id=run_id)) == 1
