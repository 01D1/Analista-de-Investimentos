import pandas as pd

from src.paper.hypothesis_oos_store import load_hypothesis_oos_coverage, load_hypothesis_oos_results, load_hypothesis_oos_runs, save_hypothesis_oos_run


def test_hypothesis_oos_store_roundtrip(tmp_path):
    db = tmp_path / "hypothesis_oos.db"
    summary = {
        "hypothesis_id": "REDUCE_VOLATILITY_EXPOSURE",
        "hypothesis_type": "REDUCE_VOLATILITY_EXPOSURE",
        "target": "portfolio",
        "windows_count": 1,
        "scenarios_count": 1,
        "positive_improvement_pct": 1,
        "mean_return_delta": 0.01,
        "mean_drawdown_delta": 0.01,
        "mean_fragility_delta": -2,
        "robustness_class": "HYPOTHESIS_PROMISING",
        "governance_status": "HYPOTHESIS_APPROVED_FOR_MORE_TESTING",
    }
    results = pd.DataFrame(
        {
            "window_id": [1],
            "scenario_name": ["BASE_COST"],
            "signal_source": ["quant"],
            "start_date": ["2026-03-01"],
            "end_date": ["2026-03-31"],
            "base_return": [0],
            "hypothesis_return": [0.01],
            "return_delta": [0.01],
            "base_drawdown": [-0.05],
            "hypothesis_drawdown": [-0.04],
            "drawdown_delta": [0.01],
            "base_fragility_score": [40],
            "hypothesis_fragility_score": [30],
            "fragility_delta": [-10],
            "trades_count": [20],
            "improvement_detected": [True],
            "overfitting_flag": [False],
            "cost_sensitivity_flag": [False],
            "regime_instability_flag": [False],
            "metadata_json": ["{}"],
        }
    )
    coverage = pd.DataFrame(
        {
            "window_id": [1],
            "scenario_name": ["BASE_COST"],
            "signal_source": ["quant"],
            "regime_filter": [""],
            "start_date": ["2026-03-01"],
            "end_date": ["2026-03-31"],
            "signals_count": [5],
            "price_days_count": [21],
            "tickers_count": [1],
            "useful_cell": [True],
            "source_coverage_status": ["COVERAGE_USEFUL"],
            "message": ["ok"],
            "metadata_json": ["{}"],
        }
    )
    run_id = save_hypothesis_oos_run(db, summary, results, coverage)
    assert run_id == 1
    assert load_hypothesis_oos_runs(db).loc[0, "hypothesis_id"] == "REDUCE_VOLATILITY_EXPOSURE"
    assert load_hypothesis_oos_results(db, run_id).loc[0, "scenario_name"] == "BASE_COST"
    assert load_hypothesis_oos_coverage(db, run_id).loc[0, "source_coverage_status"] == "COVERAGE_USEFUL"
