import pandas as pd

from src.context.event_coverage import (
    calculate_event_coverage,
    calculate_event_coverage_by_regime,
    classify_coverage_quality,
    classify_regime_event_coverage,
)


def test_calculate_event_coverage_by_ticker_month_and_source():
    signals = pd.DataFrame(
        [
            {"trade_date": "2026-01-05", "ticker": "PETR4"},
            {"trade_date": "2026-01-06", "ticker": "VALE3"},
            {"trade_date": "2026-02-01", "ticker": "ITUB4"},
        ]
    )
    events = pd.DataFrame(
        [
            {"event_date": "2026-01-05", "ticker": "PETR4", "event_source": "cvm"},
            {"event_date": "2026-01-06", "ticker": "VALE3", "event_source": "news_hunter"},
        ]
    )

    metrics = calculate_event_coverage(events, signals)

    assert metrics["total_signals"] == 3
    assert metrics["signals_with_coverage"] == 2
    assert metrics["tickers_without_events"] == ["ITUB4"]
    assert metrics["coverage_by_ticker"]["PETR4"] == 1.0
    assert metrics["coverage_by_source"]["cvm"] == 1


def test_classify_coverage_quality_flags_insufficient_and_good():
    insufficient = classify_coverage_quality({"signals_with_event_pct": 0.05, "tickers_with_event_pct": 0.1, "sources_count": 1, "months_with_events": 1})
    good = classify_coverage_quality({"signals_with_event_pct": 0.75, "tickers_with_event_pct": 0.8, "sources_count": 2, "months_with_events": 3})

    assert insufficient == "COBERTURA_INSUFICIENTE"
    assert good == "COBERTURA_BOA"


def test_calculate_event_coverage_by_regime_includes_macro_events():
    signals = pd.DataFrame(
        [
            {"trade_date": "2026-01-05", "ticker": "PETR4"},
            {"trade_date": "2026-01-05", "ticker": "VALE3"},
            {"trade_date": "2026-01-06", "ticker": "ITUB4"},
        ]
    )
    regimes = pd.DataFrame(
        [
            {"trade_date": "2026-01-05", "primary_regime": "ALTA_TENDENCIAL", "trend_regime": "ALTA_TENDENCIAL"},
            {"trade_date": "2026-01-06", "primary_regime": "LATERAL", "trend_regime": "LATERAL"},
        ]
    )
    events = pd.DataFrame(
        [
            {"event_date": "2026-01-05", "ticker": "", "event_type": "MACRO_BRASIL", "event_source": "calendario_economico"},
        ]
    )

    coverage = calculate_event_coverage_by_regime(events, signals, regimes)
    classified = classify_regime_event_coverage(coverage)

    primary = classified[classified["regime_type"] == "primary_regime"]
    alta = primary[primary["regime_value"] == "ALTA_TENDENCIAL"].iloc[0]
    lateral = primary[primary["regime_value"] == "LATERAL"].iloc[0]
    assert alta["signals_with_event"] == 2
    assert alta["dominant_event_source"] == "calendario_economico"
    assert lateral["signals_with_event"] == 0
    assert lateral["coverage_quality"] == "COBERTURA_INSUFICIENTE"
