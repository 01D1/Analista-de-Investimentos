import pandas as pd

from src.scanners import limit_signal_source_calibration


def test_limit_signal_source_calibration_cli_run_with_mocks(tmp_path, monkeypatch):
    monkeypatch.setattr(limit_signal_source_calibration, "_signals_by_source", lambda db, sources, start, end: {"quant": pd.DataFrame({"trade_date": ["2026-02-01"], "ticker": ["PETR4"], "signal_score": [80]})})
    monkeypatch.setattr(limit_signal_source_calibration, "_load_price_history", lambda db, tickers, start, end: pd.DataFrame({"trade_date": ["2026-01-01", "2026-02-01", "2026-03-01"], "ticker": ["PETR4", "PETR4", "PETR4"], "close": [10, 11, 12]}))
    monkeypatch.setattr(limit_signal_source_calibration, "load_latest_risk_snapshots", lambda db, tickers: pd.DataFrame())
    monkeypatch.setattr(limit_signal_source_calibration, "_load_regimes", lambda db, start, end: pd.DataFrame())
    monkeypatch.setattr(limit_signal_source_calibration, "run_limit_signal_source_oos", lambda *args, **kwargs: pd.DataFrame({"variant_id": ["V1"], "signal_source": ["quant"], "regime": ["SEM_REGIME"], "coverage_status": ["COVERAGE_USEFUL"], "positive_improvement_pct": [0.7], "mean_return_delta": [0.01], "mean_drawdown_delta": [0], "mean_fragility_delta": [-1], "mean_cost_drag_delta": [-1], "mean_slippage_delta": [-1], "trades_count": [100], "removed_pct": [0.1], "cost_sensitivity_flag": [False], "slippage_sensitivity_flag": [False], "overfitting_flag": [False], "low_sample_flag": [False]}))
    result = limit_signal_source_calibration.run(start="2026-01-01", end="2026-03-01", sources=["quant"], db_path=tmp_path / "mock.db")
    assert result["best_variant_id"] == "V1"


def test_limit_signal_source_calibration_main_smoke(monkeypatch):
    monkeypatch.setattr(limit_signal_source_calibration, "run", lambda **kwargs: {"status": "SUCCESS", "variants_count": 1, "oos_rows": 1, "best_variant_id": "V1", "best_score": 70, "saved_run_id": None, "csv_paths": {}})
    assert limit_signal_source_calibration.main(["--start", "2026-01-01", "--end", "2026-03-01"]) == 0

