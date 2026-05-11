import pandas as pd

from src.quant.net_backtest import (
    apply_execution_costs_to_backtest,
    generate_net_backtest_report,
    summarize_by_execution_quality,
    summarize_net_vs_gross,
)


def _backtest():
    return pd.DataFrame(
        [
            {
                "ticker": "PETR4",
                "signal_type": "FORÇA COM LIQUIDEZ",
                "score_bucket": "80_100",
                "future_return_1d": 1.0,
                "future_return_3d": 2.0,
                "future_return_5d": 3.0,
                "future_return_10d": 4.0,
                "volume": 100_000_000,
                "trades": 20_000,
                "mae_5d": -1.0,
            },
            {
                "ticker": "XYZ3",
                "signal_type": "SEM ASSIMETRIA",
                "score_bucket": "20_40",
                "future_return_1d": -0.5,
                "future_return_3d": -1.0,
                "future_return_5d": -1.5,
                "future_return_10d": -2.0,
                "volume": 100_000,
                "trades": 20,
                "mae_5d": -4.0,
            },
        ]
    )


def test_apply_execution_costs_creates_net_columns_and_tradeable_flags():
    out = apply_execution_costs_to_backtest(_backtest(), cost_bps=10, slippage_bps=5, min_volume=5_000_000)

    assert "net_return_5d" in out.columns
    assert out.loc[0, "net_return_5d"] < out.loc[0, "future_return_5d"]
    assert out.loc[0, "execution_quality"] == "EXCELENTE"
    assert bool(out.loc[0, "is_tradeable"]) is True
    assert out.loc[1, "execution_quality"] == "INVIAVEL"
    assert bool(out.loc[1, "is_tradeable"]) is False


def test_apply_execution_costs_handles_empty_data():
    out = apply_execution_costs_to_backtest(pd.DataFrame())

    assert out.empty
    assert "net_return_5d" in out.columns


def test_summarize_net_vs_gross_compares_returns_and_hits():
    out = apply_execution_costs_to_backtest(_backtest(), cost_bps=10, slippage_bps=5, min_volume=5_000_000)
    summary = summarize_net_vs_gross(out)

    assert summary["gross_mean_return_5d"] == 0.75
    assert summary["net_mean_return_5d"] < summary["gross_mean_return_5d"]
    assert summary["untradeable_signals"] == 1
    assert summary["best_net_signal_type"] == "FORÇA COM LIQUIDEZ"
    assert summary["best_net_score_bucket"] == "80_100"


def test_summarize_by_execution_quality_and_text_report():
    out = apply_execution_costs_to_backtest(_backtest(), cost_bps=10, slippage_bps=5, min_volume=5_000_000)
    by_quality = summarize_by_execution_quality(out)
    summary = summarize_net_vs_gross(out)
    report = generate_net_backtest_report(summary, summary)

    assert set(by_quality["execution_quality"]) == {"EXCELENTE", "INVIAVEL"}
    assert "Após custos" in report
    assert "retorno médio D+5" in report
