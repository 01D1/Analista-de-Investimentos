import pandas as pd

from src.quant.signal_filters import (
    apply_quality_filters,
    classify_signal_quality,
    generate_quality_filter_report,
    summarize_filter_impact,
)


def _signals():
    return pd.DataFrame(
        [
            {
                "ticker": "PETR4",
                "signal_type": "FORÇA COM LIQUIDEZ",
                "score_bucket": "80_100",
                "score_final": 88,
                "signal_confidence": "ALTA",
                "execution_quality": "EXCELENTE",
                "volume": 100_000_000,
                "trades": 20_000,
                "score_liquidez": 90,
                "score_risco": 75,
                "is_tradeable": 1,
                "future_return_5d": 1.0,
                "net_return_5d": 0.7,
            },
            {
                "ticker": "XYZ3",
                "signal_type": "SEM ASSIMETRIA",
                "score_bucket": "20_40",
                "score_final": 35,
                "signal_confidence": "BAIXA",
                "execution_quality": "INVIAVEL",
                "volume": 100_000,
                "trades": 10,
                "score_liquidez": 10,
                "score_risco": 20,
                "is_tradeable": 0,
                "future_return_5d": -1.0,
                "net_return_5d": -1.5,
            },
        ]
    )


def test_classify_signal_quality_distinguishes_high_quality_and_discard():
    high = classify_signal_quality(_signals().iloc[0])
    low = classify_signal_quality(_signals().iloc[1])

    assert high == "ALTA_QUALIDADE"
    assert low == "DESCARTAR"


def test_apply_quality_filters_removes_bad_signals_and_records_reasons():
    filtered = apply_quality_filters(
        _signals(),
        {
            "min_score_final": 80,
            "min_execution_quality": "BOA",
            "remove_inviavel": True,
            "only_tradeable": True,
        },
    )

    assert filtered["ticker"].tolist() == ["PETR4"]
    assert "signal_quality" in filtered.columns
    assert filtered["signal_quality"].iloc[0] == "ALTA_QUALIDADE"


def test_summarize_filter_impact_and_report():
    before = _signals()
    after = apply_quality_filters(before, {"min_score_final": 80, "remove_inviavel": True})
    summary = summarize_filter_impact(before, after)
    report = generate_quality_filter_report(summary)

    assert summary["signals_before"] == 2
    assert summary["signals_after"] == 1
    assert summary["removed_pct"] == 50.0
    assert summary["mean_net_return_after"] > summary["mean_net_return_before"]
    assert "reduziram os sinais" in report
