import json

import pandas as pd

from src.quant.filter_walk_forward import (
    classify_filter_robustness,
    generate_filter_walk_forward_report,
    evaluate_filter_by_regime,
    run_filter_walk_forward,
    summarize_filter_walk_forward,
)


def _rows(month: int, high_return: float, low_return: float):
    rows = []
    for day in range(1, 9):
        ticker = f"ATV{day}"
        rows.append(
            {
                "trade_date": f"2026-{month:02d}-{day:02d}",
                "ticker": ticker,
                "score_final": 85,
                "score_liquidez": 80,
                "score_risco": 70,
                "signal_confidence": 0.8,
                "execution_quality": "BOA",
                "is_tradeable": 1,
                "volume": 10_000_000,
                "signal_type": "FORÇA COM LIQUIDEZ",
                "score_bucket": "80_100",
                "net_return_5d": high_return,
            }
        )
        rows.append(
            {
                "trade_date": f"2026-{month:02d}-{day:02d}",
                "ticker": f"FRACO{day}",
                "score_final": 45,
                "score_liquidez": 30,
                "score_risco": 40,
                "signal_confidence": 0.4,
                "execution_quality": "ACEITAVEL",
                "is_tradeable": 1,
                "volume": 1_000_000,
                "signal_type": "OBSERVAR",
                "score_bucket": "40_60",
                "net_return_5d": low_return,
            }
        )
    return rows


def _robust_backtest():
    data = []
    data.extend(_rows(1, 0.5, -0.3))
    data.extend(_rows(2, 0.4, -0.4))
    data.extend(_rows(3, 0.3, -0.2))
    data.extend(_rows(4, 0.2, -0.1))
    return pd.DataFrame(data)


def _overfit_backtest():
    data = []
    data.extend(_rows(1, 0.8, -0.2))
    data.extend(_rows(2, -0.6, -0.1))
    data.extend(_rows(3, 0.7, -0.2))
    data.extend(_rows(4, -0.5, -0.1))
    return pd.DataFrame(data)


PARAM_GRID = {
    "score_final_min": [0, 80],
    "score_liquidez_min": [0, 70],
    "allowed_execution_quality": [["ACEITAVEL", "BOA", "EXCELENTE"], ["BOA", "EXCELENTE"]],
}


def test_filter_walk_forward_selects_train_thresholds_and_applies_to_test():
    results = run_filter_walk_forward(
        _robust_backtest(),
        train_months=1,
        test_months=1,
        param_grid=PARAM_GRID,
        min_samples_train=5,
        min_samples_test=5,
    )

    assert not results.empty
    assert results.loc[0, "test_mean_net_return"] > 0
    assert results.loc[0, "positive_test_window"] is True
    params = json.loads(results.loc[0, "best_params_json"])
    assert "score_final_min" in params


def test_filter_walk_forward_flags_overfitting_and_concentration():
    concentrated = _overfit_backtest()
    concentrated.loc[concentrated["score_final"] >= 80, "ticker"] = "UNICO"

    results = run_filter_walk_forward(
        concentrated,
        train_months=1,
        test_months=1,
        param_grid=PARAM_GRID,
        min_samples_train=5,
        min_samples_test=5,
    )

    assert results["overfitting_flag"].any()
    assert results["concentration_warning"].any()
    assert results["top_asset_concentration_pct"].max() >= 90


def test_summarize_and_report_filter_walk_forward():
    results = run_filter_walk_forward(
        _robust_backtest(),
        train_months=1,
        test_months=1,
        param_grid=PARAM_GRID,
        min_samples_train=5,
        min_samples_test=5,
    )
    summary = summarize_filter_walk_forward(results)
    report = generate_filter_walk_forward_report(summary, results)

    assert summary["windows_count"] >= 2
    assert summary["positive_windows_pct"] >= 60
    assert summary["robustness_class"] in {"ROBUSTO", "PROMISSOR"}
    assert "fora da amostra" in report


def test_classify_filter_robustness_variants():
    assert (
        classify_filter_robustness(
            {
                "windows_count": 6,
                "positive_windows_pct": 70,
                "mean_test_net_return": 0.2,
                "mean_test_hit_rate": 0.55,
                "avg_test_signals": 80,
                "avg_top_3_concentration_pct": 35,
                "overfitting_alert": False,
            }
        )
        == "ROBUSTO"
    )
    assert (
        classify_filter_robustness(
            {
                "windows_count": 6,
                "positive_windows_pct": 20,
                "mean_test_net_return": -0.2,
                "mean_test_hit_rate": 0.45,
                "avg_test_signals": 80,
                "avg_top_3_concentration_pct": 80,
                "overfitting_alert": True,
            }
        )
        == "OVERFIT_PROVAVEL"
    )
    assert classify_filter_robustness({"windows_count": 1, "avg_test_signals": 3}) == "AMOSTRA_INSUFICIENTE"


def test_evaluate_filter_by_regime_summarizes_regime_performance():
    backtest = _robust_backtest()
    backtest["primary_regime"] = ["ALTA_TENDENCIAL" if i % 2 == 0 else "ALTA_VOLATILIDADE" for i in range(len(backtest))]
    summary = evaluate_filter_by_regime(pd.DataFrame(), backtest)

    assert "primary_regime" in summary.columns
    assert set(summary["primary_regime"]) == {"ALTA_TENDENCIAL", "ALTA_VOLATILIDADE"}
