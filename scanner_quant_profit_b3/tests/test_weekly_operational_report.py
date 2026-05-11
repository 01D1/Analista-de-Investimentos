import pandas as pd

from src.reports.weekly_operational_report import build_weekly_operational_report, save_weekly_report


def test_weekly_operational_report_contains_sections(tmp_path):
    source_sla = pd.DataFrame(
        [{"source_name": "csv", "availability_pct": 100, "reliability_class": "BOA", "latest_status": "OK", "days_since_last_ok": 0}]
    )
    routine = {"routine_health_status": "OK", "total_runs": 5, "success_rate_pct": 100, "failure_rate_pct": 0, "avg_alerts_count": 0}
    alerts = {"total_alerts": 0, "open_alerts": 0, "critical_count": 0, "warning_count": 0, "most_problematic_source": "", "most_common_alert_type": ""}
    coverage = pd.DataFrame([{"period": "2026-05", "avg_signals_with_event_pct": 0.1, "avg_tickers_with_event_pct": 0.5, "coverage_trend_direction": "MELHORANDO"}])
    contracts = pd.DataFrame([{"source_name": "csv", "contract_status": "PASS", "severity": "INFO"}])

    markdown = build_weekly_operational_report(source_sla, routine, alerts, coverage, contracts)
    path = save_weekly_report(markdown, tmp_path)

    assert "Sumário Executivo" in markdown
    assert "Saúde Das Fontes" in markdown
    assert path.exists()
