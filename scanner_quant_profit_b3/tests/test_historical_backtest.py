import pandas as pd

from src.quant.historical_backtest import (
    generate_historical_backtest_report,
    run_historical_backtest,
    summarize_backtest_by_component_quantile,
    summarize_backtest_by_score_bucket,
    summarize_backtest_by_signal_type,
)


def _scored():
    rows = []
    closes = [10, 11, 12, 11.5, 13, 14, 13.5]
    for i, date in enumerate(pd.date_range("2026-01-01", periods=len(closes), freq="D")):
        rows.append(
            {
                "trade_date": date.strftime("%Y-%m-%d"),
                "ticker": "PETR4",
                "open": closes[i] - 0.2,
                "high": closes[i] + 0.5,
                "low": closes[i] - 0.5,
                "close": closes[i],
                "score_final": 85 if i < 4 else 55,
                "score_momentum": 90 - i,
                "score_tendencia": 80,
                "score_liquidez": 70,
                "score_volatilidade": 60,
                "score_risco": 75,
                "signal_type": "FORÇA COM LIQUIDEZ" if i < 4 else "OBSERVAR",
                "signal_confidence": "ALTA" if i < 4 else "MEDIA",
            }
        )
    return pd.DataFrame(rows)


def test_run_historical_backtest_calculates_forward_returns_and_excursions():
    out = run_historical_backtest(_scored(), horizons=[1, 3, 5])

    first = out.iloc[0]
    assert first["future_return_1d"] == 10.0
    assert first["future_return_3d"] == 15.0
    assert bool(first["hit_1d"]) is True
    assert "max_favorable_excursion_5d" in out.columns
    assert "score_bucket" in out.columns


def test_historical_backtest_summaries_group_by_signal_and_bucket():
    out = run_historical_backtest(_scored(), horizons=[1, 3, 5])
    by_signal = summarize_backtest_by_signal_type(out)
    by_bucket = summarize_backtest_by_score_bucket(out)

    assert "FORÇA COM LIQUIDEZ" in by_signal["signal_type"].tolist()
    assert "80_100" in by_bucket["score_bucket"].tolist()
    assert "mean_return_1d" in by_signal.columns
    assert "hit_rate_3d" in by_bucket.columns


def test_component_quantile_summary_and_report_are_textual():
    out = run_historical_backtest(_scored(), horizons=[1, 3, 5])
    components = summarize_backtest_by_component_quantile(out, quantiles=2)
    report = generate_historical_backtest_report(
        summarize_backtest_by_signal_type(out),
        summarize_backtest_by_score_bucket(out),
        "score_momentum teve relação positiva com retorno D+3.",
    )

    assert "score_momentum" in components["component"].tolist()
    assert "Foram analisados" in report
    assert "score_momentum teve relação positiva" in report
