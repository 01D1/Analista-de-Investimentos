import pandas as pd

from src.scanners import cost_frontier_analysis


def test_cost_frontier_analysis_run(monkeypatch, tmp_path):
    source = pd.DataFrame(
        [
            {"variant_id": "A", "variant_type": "exit", "cost_reduction_pct": 0.2, "return_delta": 0.01, "drawdown_delta": 0.01, "turnover_delta": -1, "trades_count": 10, "governance_status": "COST_REDUCTION_OBSERVATION_ONLY"},
            {"variant_id": "B", "variant_type": "exit", "cost_reduction_pct": 0.1, "return_delta": -0.02, "drawdown_delta": -0.01, "turnover_delta": 1, "trades_count": 10, "governance_status": "COST_REDUCTION_REJECTED"},
        ]
    )
    monkeypatch.setattr(cost_frontier_analysis, "load_cost_reduction_results", lambda db, run_id=None: source)

    result = cost_frontier_analysis.run(3, save_db=False, csv=False, db_path=tmp_path / "x.db")

    assert result["status"] == "SUCCESS"
    assert result["variants_count"] == 2
    assert result["efficient_count"] >= 1
