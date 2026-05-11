import pandas as pd

from src.context.coverage_trends import (
    calculate_event_coverage_trend,
    calculate_regime_coverage_trend,
    generate_coverage_trend_report,
)


def test_event_coverage_trend_detects_improving():
    runs = pd.DataFrame(
        [
            {"created_at": "2026-01-05", "signals_with_event_pct": 0.01, "tickers_with_event_pct": 0.1, "events_loaded": 3, "events_after_dedup": 3, "sources": "csv", "coverage_quality": "COBERTURA_INSUFICIENTE"},
            {"created_at": "2026-02-05", "signals_with_event_pct": 0.2, "tickers_with_event_pct": 0.4, "events_loaded": 30, "events_after_dedup": 28, "sources": "csv,news", "coverage_quality": "COBERTURA_MEDIA"},
        ]
    )

    trend = calculate_event_coverage_trend(runs, freq="M")

    assert trend.iloc[-1]["coverage_trend_direction"] == "MELHORANDO"
    assert trend.iloc[-1]["best_coverage_quality"] == "COBERTURA_MEDIA"


def test_event_coverage_trend_detects_worsening():
    runs = pd.DataFrame(
        [
            {"created_at": "2026-01-05", "signals_with_event_pct": 0.3, "tickers_with_event_pct": 0.5, "events_loaded": 30, "events_after_dedup": 30, "sources": "csv,news", "coverage_quality": "COBERTURA_MEDIA"},
            {"created_at": "2026-02-05", "signals_with_event_pct": 0.01, "tickers_with_event_pct": 0.1, "events_loaded": 3, "events_after_dedup": 3, "sources": "csv", "coverage_quality": "COBERTURA_INSUFICIENTE"},
        ]
    )

    trend = calculate_event_coverage_trend(runs, freq="M")

    assert trend.iloc[-1]["coverage_trend_direction"] == "PIORANDO"


def test_regime_coverage_trend_and_report():
    by_regime = pd.DataFrame(
        [
            {"coverage_run_id": 1, "regime_type": "primary_regime", "regime_value": "LATERAL", "signals_with_event_pct": 0.0, "coverage_quality": "COBERTURA_INSUFICIENTE"},
            {"coverage_run_id": 2, "regime_type": "primary_regime", "regime_value": "LATERAL", "signals_with_event_pct": 0.1, "coverage_quality": "COBERTURA_FRACA"},
        ]
    )
    coverage = pd.DataFrame(
        [
            {"created_at": "2026-01-05", "signals_with_event_pct": 0.01, "tickers_with_event_pct": 0.1, "events_loaded": 3, "events_after_dedup": 3, "sources": "csv", "coverage_quality": "COBERTURA_INSUFICIENTE"},
        ]
    )

    regime = calculate_regime_coverage_trend(by_regime)
    report = generate_coverage_trend_report(calculate_event_coverage_trend(coverage), regime)

    assert regime.loc[0, "regimes_without_coverage_count"] == 1
    assert "cobertura" in report.lower()
