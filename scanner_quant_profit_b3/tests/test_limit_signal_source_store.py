import pandas as pd

from src.paper.limit_signal_source_store import load_limit_signal_source_variant_results, load_limit_signal_source_variant_runs, save_limit_signal_source_variant_run


def test_limit_signal_source_store_roundtrip(tmp_path):
    db = tmp_path / "limit.db"
    ranked = pd.DataFrame({"variant_id": ["V1"], "variant_robustness_score": [70], "variant_class": ["VARIANT_PROMISING"], "governance_status": ["LIMIT_SOURCE_MORE_TESTING_REQUIRED"]})
    oos = pd.DataFrame({"variant_id": ["V1"], "signal_source": ["quant"], "cost_scenario": ["BASE_COST"], "slippage_scenario": ["BASE_SLIPPAGE"], "regime": ["SEM_REGIME"], "windows_count": [1], "trades_count": [10], "remaining_signals": [10], "removed_pct": [0.1], "mean_return_delta": [0.01], "mean_drawdown_delta": [0], "mean_fragility_delta": [-1], "mean_cost_drag_delta": [-1], "mean_slippage_delta": [-1], "positive_improvement_pct": [0.7], "metadata_json": ["{}"]})
    run_id = save_limit_signal_source_variant_run(db, ranked, oos, start_date="2026-01-01", end_date="2026-03-01")
    assert run_id == 1
    assert load_limit_signal_source_variant_runs(db).loc[0, "best_variant_id"] == "V1"
    assert load_limit_signal_source_variant_results(db, run_id=1).loc[0, "variant_robustness_score"] == 70

