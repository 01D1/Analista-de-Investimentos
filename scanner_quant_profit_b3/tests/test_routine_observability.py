import pandas as pd

from src.context.routine_observability import (
    generate_routine_observability_report,
    summarize_daily_routine_runs,
)


def test_routine_observability_success_summary():
    runs = pd.DataFrame(
        [
            {
                "started_at": pd.Timestamp.now().isoformat(),
                "status": "SUCCESS",
                "events_loaded": 10,
                "signals_covered_pct": 0.12,
                "alerts_count": 0,
            },
            {
                "started_at": pd.Timestamp.now().isoformat(),
                "status": "SUCCESS_WITH_WARNINGS",
                "events_loaded": 20,
                "signals_covered_pct": 0.18,
                "alerts_count": 2,
            },
        ]
    )

    summary = summarize_daily_routine_runs(runs, window_days=30)

    assert summary["total_runs"] == 2
    assert summary["success_rate_pct"] == 100
    assert summary["warning_rate_pct"] == 50
    assert summary["routine_health_status"] == "WARNING"
    assert summary["avg_events_loaded"] == 15


def test_routine_observability_failed_summary_is_critical():
    runs = pd.DataFrame(
        [
            {
                "started_at": pd.Timestamp.now().isoformat(),
                "status": "FAILED",
                "events_loaded": 0,
                "signals_covered_pct": 0,
                "alerts_count": 3,
            }
        ]
    )

    summary = summarize_daily_routine_runs(runs, window_days=30)

    assert summary["failed_count"] == 1
    assert summary["routine_health_status"] == "CRITICAL"


def test_routine_observability_empty_report():
    summary = summarize_daily_routine_runs(pd.DataFrame(), window_days=30)
    report = generate_routine_observability_report(summary)

    assert summary["routine_health_status"] == "NO_RUNS"
    assert "não possui execuções" in report
