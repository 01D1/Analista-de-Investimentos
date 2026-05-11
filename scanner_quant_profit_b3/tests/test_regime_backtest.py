import pandas as pd

from src.quant.regime_backtest import (
    compare_regime_performance,
    generate_regime_report,
    summarize_backtest_by_regime,
)


def _backtest():
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "primary_regime": "ALTA_TENDENCIAL",
                "trend_regime": "ALTA_TENDENCIAL",
                "volatility_regime": "BAIXA_VOLATILIDADE",
                "liquidity_regime": "LIQUIDEZ_FORTE",
                "risk_regime": "RISCO_CONTROLADO",
                "future_return_5d": 0.8,
                "net_return_5d": 0.5,
                "signal_type": "FORÇA COM LIQUIDEZ",
                "score_bucket": "80_100",
                "execution_quality": "BOA",
                "is_tradeable": 1,
                "mae_5d": -0.5,
            },
            {
                "ticker": "BBB",
                "primary_regime": "ALTA_VOLATILIDADE",
                "trend_regime": "LATERAL",
                "volatility_regime": "ALTA_VOLATILIDADE",
                "liquidity_regime": "LIQUIDEZ_FRACA",
                "risk_regime": "RISCO_ELEVADO",
                "future_return_5d": -0.4,
                "net_return_5d": -0.7,
                "signal_type": "OBSERVAR",
                "score_bucket": "40_60",
                "execution_quality": "RUIM",
                "is_tradeable": 0,
                "mae_5d": -2.0,
            },
        ]
    )


def test_summarize_backtest_by_regime_groups_core_metrics():
    summary = summarize_backtest_by_regime(_backtest())

    assert {"regime_type", "regime_value", "signals_count", "mean_net_return_5d"}.issubset(summary.columns)
    alta = summary[(summary["regime_type"] == "primary_regime") & (summary["regime_value"] == "ALTA_TENDENCIAL")].iloc[0]
    assert alta["mean_net_return_5d"] == 0.5
    assert alta["tradeable_pct"] == 100.0


def test_compare_and_report_regime_performance():
    summary = summarize_backtest_by_regime(_backtest())
    comparison = compare_regime_performance(summary, min_samples=1)
    report = generate_regime_report(summary)

    assert "best_regimes" in comparison
    assert "ALTA_TENDENCIAL" in comparison["best_regimes"]
    assert "ALTA_VOLATILIDADE" in comparison["weak_regimes"]
    assert "regimes" in report
