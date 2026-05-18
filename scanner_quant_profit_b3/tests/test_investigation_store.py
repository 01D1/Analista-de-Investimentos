import pandas as pd

from src.paper.investigation_store import load_investigation_results, load_investigation_runs, save_investigation_run


def test_investigation_store_roundtrip(tmp_path):
    db = tmp_path / "investigation.db"
    summary = {
        "base_paper_run_id": 2,
        "base_fragility_run_id": 1,
        "hypotheses_count": 1,
        "improved_count": 1,
        "rejected_count": 0,
        "observation_count": 0,
        "best_hypothesis_id": "EXCLUDE_ASSET_ITUB4",
        "best_improvement_score": 50,
    }
    results = pd.DataFrame(
        {
            "hypothesis_id": ["EXCLUDE_ASSET_ITUB4"],
            "hypothesis_type": ["EXCLUDE_ASSET"],
            "target": ["ITUB4"],
            "title": ["Investigar exclusao simulada"],
            "simulated_return": [0.02],
            "simulated_drawdown": [-0.05],
            "simulated_trades": [30],
            "simulated_win_rate": [0.6],
            "simulated_profit_factor": [1.5],
            "fragility_score_before": [70],
            "fragility_score_after": [30],
            "improvement_score": [50],
            "governance_status": ["INVESTIGATION_APPROVED_FOR_FURTHER_TEST"],
            "conclusion": ["INVESTIGATION_IMPROVED"],
            "metadata_json": ["{}"],
        }
    )
    run_id = save_investigation_run(db, summary, results)
    assert run_id == 1
    assert load_investigation_runs(db).loc[0, "best_hypothesis_id"] == "EXCLUDE_ASSET_ITUB4"
    assert load_investigation_results(db, run_id).loc[0, "target"] == "ITUB4"
