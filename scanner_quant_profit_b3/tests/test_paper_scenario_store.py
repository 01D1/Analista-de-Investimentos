import pandas as pd

from src.paper.paper_scenario_store import (
    load_paper_cost_sensitivity_results,
    load_paper_scenario_validation_results,
    load_paper_scenario_validation_runs,
    load_paper_signal_source_comparison,
    save_paper_scenario_validation_run,
)


def test_paper_scenario_store_roundtrip(tmp_path):
    db = tmp_path / "scenario.db"
    summary = {"status": "COMPLETED", "periods_count": 1, "scenarios_count": 1, "signal_sources_count": 1, "positive_periods_pct": 1, "mean_return": 0.01, "mean_drawdown": -0.02, "governance_status": "PAPER_SCENARIO_PROMISING"}
    results = pd.DataFrame({"period_id": [1], "scenario_id": ["S"], "scenario_name": ["S"], "signal_source": ["quant"], "start_date": ["2026-01-01"], "end_date": ["2026-01-31"], "total_return": [0.01], "max_drawdown": [-0.02], "sharpe": [1], "sortino": [1], "win_rate": [0.6], "profit_factor": [1.2], "trades_count": [10], "turnover": [10], "cost_bps": [10], "slippage_bps": [5], "governance_status": ["PAPER_APPROVED_FOR_REVIEW"], "metadata_json": ["{}"]})
    costs = pd.DataFrame({"cost_scenario": ["COST_BASE"], "cost_bps": [10], "slippage_bps": [5], "mean_return": [0.01], "mean_drawdown": [-0.02], "positive_periods_pct": [1], "cost_robustness_class": ["COST_ROBUST"], "metadata_json": ["{}"]})
    sources = pd.DataFrame({"signal_source": ["quant"], "mean_return": [0.01], "mean_drawdown": [-0.02], "win_rate": [0.6], "profit_factor": [1.2], "trades_count": [10], "robustness_class": ["SIGNAL_SOURCE_PROMISSOR"], "metadata_json": ["{}"]})
    run_id = save_paper_scenario_validation_run(db, summary, results, costs, sources)
    assert run_id == 1
    assert len(load_paper_scenario_validation_runs(db)) == 1
    assert len(load_paper_scenario_validation_results(db, run_id)) == 1
    assert len(load_paper_cost_sensitivity_results(db, run_id)) == 1
    assert len(load_paper_signal_source_comparison(db, run_id)) == 1
