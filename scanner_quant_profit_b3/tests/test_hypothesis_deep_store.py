import pandas as pd

from src.paper.hypothesis_deep_store import load_hypothesis_block_reasons, load_hypothesis_deep_oos_results, load_hypothesis_deep_oos_runs, save_hypothesis_deep_oos_run


def test_hypothesis_deep_store_roundtrip(tmp_path):
    db = tmp_path / "deep.db"
    results = pd.DataFrame(
        {
            "hypothesis_id": ["H1"],
            "signal_source": ["quant"],
            "cost_scenario": ["BASE_COST"],
            "slippage_scenario": ["BASE_SLIPPAGE"],
            "regime": ["SEM_REGIME"],
            "ticker": ["TODOS"],
            "windows_count": [2],
            "trades_count": [10],
            "mean_return_delta": [0.01],
            "mean_drawdown_delta": [0.0],
            "mean_fragility_delta": [-1],
            "positive_improvement_pct": [0.7],
            "block_reason": ["NO_CLEAR_BLOCKER"],
            "governance_status": ["HYPOTHESIS_DEEP_APPROVED_FOR_OBSERVATION"],
        }
    )
    reasons = pd.DataFrame({"hypothesis_id": ["H1"], "primary_block_reason": ["NO_CLEAR_BLOCKER"], "secondary_block_reason": [""], "explanation": ["ok"], "required_actions_json": ["[]"], "metadata_json": ["{}"]})
    run_id = save_hypothesis_deep_oos_run(db, results, reasons, start_date="2026-01-01", end_date="2026-03-01")
    assert run_id == 1
    assert load_hypothesis_deep_oos_runs(db).loc[0, "best_hypothesis_id"] == "H1"
    assert load_hypothesis_deep_oos_results(db, run_id=1).loc[0, "block_reason"] == "NO_CLEAR_BLOCKER"
    assert load_hypothesis_block_reasons(db, run_id=1).loc[0, "primary_block_reason"] == "NO_CLEAR_BLOCKER"
