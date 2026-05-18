import pandas as pd

from src.scanners import hypothesis_ranking


def test_hypothesis_ranking_cli_run_with_mocks(tmp_path, monkeypatch):
    monkeypatch.setattr(hypothesis_ranking, "build_default_hypothesis_universe", lambda: pd.DataFrame({"hypothesis_id": ["H1"], "hypothesis_type": ["H1"], "can_simulate": [True]}))
    monkeypatch.setattr(hypothesis_ranking, "_signals_by_source", lambda db, sources, start, end: {"quant": pd.DataFrame({"trade_date": ["2026-02-01"], "ticker": ["PETR4"], "signal_source": ["quant"]})})
    monkeypatch.setattr(hypothesis_ranking, "_load_price_history", lambda db, tickers, start, end: pd.DataFrame({"trade_date": ["2026-02-01"], "ticker": ["PETR4"], "close": [10]}))
    monkeypatch.setattr(hypothesis_ranking, "load_latest_risk_snapshots", lambda db, tickers: pd.DataFrame())
    monkeypatch.setattr(hypothesis_ranking, "run_hypothesis_multi_source_validation", lambda *args, **kwargs: pd.DataFrame({"hypothesis_id": ["H1"], "signal_source": ["quant"], "scenario_name": ["BASE"], "windows_count": [1], "useful_cells": [1], "positive_improvement_pct": [1.0], "mean_return_delta": [0.01], "mean_drawdown_delta": [0.01], "mean_fragility_delta": [-5], "mean_cost_drag_delta": [0], "overfitting_flag": [False], "cost_sensitivity_flag": [False], "regime_instability_flag": [False], "data_coverage_status": ["COVERAGE_USEFUL"]}))
    result = hypothesis_ranking.run(start="2026-01-01", end="2026-03-01", sources=["quant"], db_path=tmp_path / "mock.db")
    assert result["best_hypothesis_id"] == "H1"


def test_hypothesis_ranking_main_smoke(monkeypatch):
    monkeypatch.setattr(hypothesis_ranking, "run", lambda **kwargs: {"status": "SUCCESS", "hypotheses_count": 1, "validation_rows": 1, "ranked_rows": 1, "best_hypothesis_id": "H1", "best_score": 70, "saved_run_id": None, "csv_paths": {}})
    assert hypothesis_ranking.main(["--start", "2026-01-01", "--end", "2026-03-01"]) == 0

