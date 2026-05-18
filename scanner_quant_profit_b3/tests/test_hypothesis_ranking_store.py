import pandas as pd

from src.paper.hypothesis_ranking_store import load_hypothesis_ranking_results, load_hypothesis_ranking_runs, save_hypothesis_ranking_run


def test_hypothesis_ranking_store_roundtrip(tmp_path):
    db = tmp_path / "ranking.db"
    ranked = pd.DataFrame(
        [
            {
                "hypothesis_id": "H1",
                "signal_source": "MULTI_SOURCE",
                "scenario_name": "ALL",
                "positive_improvement_pct": 0.6,
                "mean_return_delta": 0.01,
                "mean_drawdown_delta": 0.01,
                "mean_fragility_delta": -5,
                "cost_sensitivity_flag": False,
                "overfitting_flag": False,
                "source_diversity_score": 100,
                "hypothesis_robustness_score": 75,
                "hypothesis_class": "HYPOTHESIS_ROBUST",
                "governance_status": "HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION",
                "metadata_json": "{}",
            }
        ]
    )
    run_id = save_hypothesis_ranking_run(db, ranked, pd.DataFrame({"signal_source": ["quant"], "scenario_name": ["BASE"]}))
    assert run_id == 1
    assert load_hypothesis_ranking_runs(db).loc[0, "best_hypothesis_id"] == "H1"
    assert load_hypothesis_ranking_results(db, run_id=1).loc[0, "hypothesis_robustness_score"] == 75

