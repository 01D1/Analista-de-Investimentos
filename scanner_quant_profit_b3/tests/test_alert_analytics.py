import pandas as pd

from src.notifications.alert_analytics import detect_recurring_alerts, generate_alerts_report, summarize_alerts


def test_alert_summary_counts_open_and_critical():
    alerts = pd.DataFrame(
        [
            {"created_at": "2026-05-01", "alert_type": "SOURCE_STALE", "severity": "WARNING", "source": "csv", "resolved": 0},
            {"created_at": "2026-05-02", "alert_type": "SOURCE_MISSING", "severity": "CRITICAL", "source": "news", "resolved": 1, "resolved_at": "2026-05-02T02:00:00"},
        ]
    )

    summary = summarize_alerts(alerts, window_days=30)

    assert summary["total_alerts"] == 2
    assert summary["critical_count"] == 1
    assert summary["open_alerts"] == 1
    assert summary["most_problematic_source"] in {"csv", "news"}


def test_detect_recurring_alerts():
    alerts = pd.DataFrame(
        [
            {"alert_type": "SOURCE_STALE", "severity": "WARNING", "source": "csv"},
            {"alert_type": "SOURCE_STALE", "severity": "WARNING", "source": "csv"},
            {"alert_type": "SOURCE_STALE", "severity": "WARNING", "source": "csv"},
        ]
    )

    recurring = detect_recurring_alerts(alerts, min_occurrences=3)

    assert recurring.loc[0, "occurrences"] == 3


def test_generate_alerts_report_empty_and_non_empty():
    assert "Nenhum alerta" in generate_alerts_report({"total_alerts": 0})
    report = generate_alerts_report({"total_alerts": 4, "critical_count": 1, "most_problematic_source": "csv", "most_common_alert_type": "SOURCE_STALE"})
    assert "csv" in report
