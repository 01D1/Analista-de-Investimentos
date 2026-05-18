import pandas as pd

from src.scanners import hypothesis_deep_dive


def test_hypothesis_deep_dive_cli_run_with_mocks(tmp_path, monkeypatch):
    monkeypatch.setattr(hypothesis_deep_dive, "load_hypothesis_ranking_results", lambda db, run_id=None: pd.DataFrame({"hypothesis_id": ["H1"], "hypothesis_robustness_score": [80], "hypothesis_class": ["HYPOTHESIS_FRAGILE"], "governance_status": ["R"]}))
    monkeypatch.setattr(hypothesis_deep_dive, "build_default_hypothesis_universe", lambda: pd.DataFrame({"hypothesis_id": ["H1"], "hypothesis_type": ["LIMIT_ASSET_WEIGHT"], "parameters_json": ["{}"], "can_simulate": [True]}))
    monkeypatch.setattr(hypothesis_deep_dive, "_signals_by_source", lambda db, sources, start, end: {"quant": pd.DataFrame({"trade_date": ["2026-02-01"], "ticker": ["PETR4"], "signal_score": [80]})})
    monkeypatch.setattr(hypothesis_deep_dive, "_load_price_history", lambda db, tickers, start, end: pd.DataFrame({"trade_date": ["2026-01-01", "2026-02-01", "2026-03-01"], "ticker": ["PETR4", "PETR4", "PETR4"], "close": [10, 11, 12]}))
    monkeypatch.setattr(hypothesis_deep_dive, "load_latest_risk_snapshots", lambda db, tickers: pd.DataFrame())
    monkeypatch.setattr(hypothesis_deep_dive, "_load_regimes", lambda db, start, end: pd.DataFrame())
    monkeypatch.setattr(hypothesis_deep_dive, "run_deep_oos_validation", lambda *args, **kwargs: pd.DataFrame({"hypothesis_id": ["H1"], "signal_source": ["quant"], "cost_scenario": ["BASE_COST"], "slippage_scenario": ["BASE_SLIPPAGE"], "regime": ["SEM_REGIME"], "ticker": ["TODOS"], "windows_count": [1], "trades_count": [5], "mean_return_delta": [0.01], "mean_drawdown_delta": [0.0], "mean_fragility_delta": [-1], "positive_improvement_pct": [0.8], "overfitting_flag": [False], "cost_sensitivity_flag": [False], "slippage_sensitivity_flag": [False], "regime_instability_flag": [False], "asset_concentration_flag": [False], "data_coverage_status": ["COVERAGE_USEFUL"], "block_reason": ["NO_CLEAR_BLOCKER"]}))
    result = hypothesis_deep_dive.run(ranking_run_id=1, top_n=1, db_path=tmp_path / "mock.db")
    assert result["deep_rows"] == 1
    assert result["selected_hypotheses"].loc[0, "hypothesis_id"] == "H1"


def test_hypothesis_deep_dive_main_smoke(monkeypatch):
    monkeypatch.setattr(hypothesis_deep_dive, "run", lambda **kwargs: {"status": "SUCCESS", "selected_hypotheses": pd.DataFrame({"hypothesis_id": ["H1"]}), "deep_rows": 1, "block_reasons_rows": 1, "saved_run_id": None, "csv_paths": {}})
    assert hypothesis_deep_dive.main(["--ranking-run-id", "1", "--top-n", "1"]) == 0
