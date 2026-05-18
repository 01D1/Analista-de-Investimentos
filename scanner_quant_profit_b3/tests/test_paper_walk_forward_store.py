import pandas as pd

from src.paper.paper_walk_forward_store import (
    load_paper_exit_optimization_results,
    load_paper_exit_optimization_runs,
    load_paper_simulation_comparisons,
    load_paper_walk_forward_results,
    load_paper_walk_forward_runs,
    save_paper_exit_optimization_run,
    save_paper_simulation_comparison,
    save_paper_walk_forward_run,
)


def test_paper_walk_forward_store_roundtrip(tmp_path):
    db = tmp_path / "paper_wf.db"
    results = pd.DataFrame({"window_id": [1], "train_start": ["2026-01-01"], "train_end": ["2026-02-28"], "test_start": ["2026-03-01"], "test_end": ["2026-03-31"], "best_params_json": ["{}"], "train_return": [0.02], "test_return": [0.01], "train_drawdown": [-0.02], "test_drawdown": [-0.01], "train_profit_factor": [1.2], "test_profit_factor": [1.1], "train_trades": [20], "test_trades": [10], "test_positive": [True], "overfitting_flag": [False], "turnover_warning": [False], "drawdown_warning": [False], "metadata_json": ["{}"]})
    summary = {"status": "COMPLETED", "windows_count": 1, "positive_windows_pct": 1, "mean_test_return": 0.01, "mean_test_drawdown": -0.01, "mean_test_profit_factor": 1.1, "robustness_class": "PAPER_WF_DADOS_INSUFICIENTES", "governance_status": "PAPER_OOS_BLOCKED_DATA"}
    run_id = save_paper_walk_forward_run(db, summary, results)
    assert run_id == 1
    assert len(load_paper_walk_forward_runs(db)) == 1
    assert len(load_paper_walk_forward_results(db, run_id)) == 1


def test_paper_optimization_and_comparison_store(tmp_path):
    db = tmp_path / "paper_opt.db"
    opt = pd.DataFrame({"params_json": ["{}"], "total_return": [0.01], "max_drawdown": [-0.02], "sharpe": [1], "sortino": [1], "win_rate": [0.6], "profit_factor": [1.2], "trades_count": [20], "turnover": [20], "score_objective": [0.5], "overfit_risk_hint": ["NORMAL"], "metadata_json": ["{}"]})
    opt_id = save_paper_exit_optimization_run(db, {"objective": "total_return"}, opt)
    assert opt_id == 1
    assert len(load_paper_exit_optimization_runs(db)) == 1
    assert len(load_paper_exit_optimization_results(db, opt_id)) == 1
    comparison = pd.DataFrame({"metric": ["total_return"], "simple_value": [0], "advanced_value": [0.01], "delta": [0.01], "improved": [True], "material_change": [True]})
    assert save_paper_simulation_comparison(db, 1, 2, comparison) == 1
    assert len(load_paper_simulation_comparisons(db)) == 1
