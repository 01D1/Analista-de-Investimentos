import pandas as pd

from src.quant.walk_forward import (
    create_walk_forward_windows,
    run_walk_forward_analysis,
    summarize_walk_forward_results,
)


def _wf_df():
    rows = []
    for i, date in enumerate(pd.date_range("2024-01-01", periods=24, freq="MS")):
        first_half = i < 12
        rows.append(
            {
                "trade_date": date.strftime("%Y-%m-%d"),
                "ticker": "PETR4",
                "signal_type": "FORÇA COM LIQUIDEZ" if first_half else "FORÇA COM LIQUIDEZ",
                "score_bucket": "80_100" if first_half else "80_100",
                "score_final": 85,
                "future_return_3d": 2.0 if first_half else -1.0,
                "future_return_5d": 3.0 if first_half else -2.0,
                "future_return_10d": 4.0 if first_half else -3.0,
            }
        )
    return pd.DataFrame(rows)


def test_create_walk_forward_windows_uses_rolling_months():
    windows = create_walk_forward_windows("2024-01-01", "2025-12-31", train_months=12, test_months=3)

    assert len(windows) >= 4
    assert windows[0]["train_start"] == "2024-01-01"
    assert windows[0]["test_start"] == "2025-01-01"
    assert windows[1]["train_start"] == "2024-04-01"


def test_run_walk_forward_analysis_detects_test_degradation():
    walk = run_walk_forward_analysis(_wf_df(), train_months=12, test_months=3, horizon=5)

    assert not walk.empty
    assert "degradation_score" in walk.columns
    assert walk["overfitting_flag"].any()


def test_run_walk_forward_analysis_can_use_net_returns():
    df = _wf_df()
    df["net_return_5d"] = df["future_return_5d"] - 0.5

    walk = run_walk_forward_analysis(df, train_months=12, test_months=3, horizon=5, return_prefix="net_return")

    assert not walk.empty
    assert walk["return_mode"].eq("net_return").all()


def test_summarize_walk_forward_results_reports_overfitting():
    walk = run_walk_forward_analysis(_wf_df(), train_months=12, test_months=3, horizon=5)
    summary = summarize_walk_forward_results(walk)

    assert summary["windows_count"] == len(walk)
    assert "overfitting_alert" in summary
    assert "relatorio" in summary
