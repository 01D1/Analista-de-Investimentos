import pandas as pd

from src.quant.out_of_sample import (
    compare_train_test,
    evaluate_train_test_performance,
    split_train_test_by_date,
)


def _backtest_df():
    rows = []
    for i, date in enumerate(pd.date_range("2024-01-01", periods=8, freq="MS")):
        strong = i < 4
        rows.append(
            {
                "trade_date": date.strftime("%Y-%m-%d"),
                "ticker": "PETR4",
                "signal_type": "FORÇA COM LIQUIDEZ" if strong else "SEM ASSIMETRIA",
                "score_bucket": "80_100" if strong else "20_40",
                "score_final": 85 if strong else 30,
                "future_return_1d": 1.0 if strong else -0.5,
                "future_return_3d": 2.0 if strong else -1.0,
                "future_return_5d": 3.0 if strong else -1.5,
                "future_return_10d": 4.0 if strong else -2.0,
            }
        )
    return pd.DataFrame(rows)


def test_split_train_test_by_date_separates_after_cutoff():
    train, test = split_train_test_by_date(_backtest_df(), "2024-04-01")

    assert len(train) == 4
    assert len(test) == 4
    assert train["trade_date"].max() == "2024-04-01"
    assert test["trade_date"].min() == "2024-05-01"


def test_evaluate_train_test_performance_returns_group_summaries():
    result = evaluate_train_test_performance(_backtest_df(), "2024-04-01")

    assert result["train"]["signals"] == 4
    assert result["test"]["signals"] == 4
    assert result["train"]["mean_return_5d"] == 3.0
    assert result["test"]["mean_return_5d"] == -1.5
    assert "by_signal_type" in result["train"]
    assert "by_score_bucket" in result["test"]


def test_compare_train_test_flags_degradation_and_overfitting():
    result = evaluate_train_test_performance(_backtest_df(), "2024-04-01")
    comparison = compare_train_test(result["train"], result["test"])

    assert comparison["performance_degraded"] is True
    assert comparison["overfitting_alert"] is True
    assert "caiu" in comparison["diagnosis"]
