import pandas as pd

from src.context.observability_store import (
    load_latest_observability_snapshot,
    load_observability_history,
    save_operational_observability_snapshot,
    save_source_sla_snapshot,
)


def test_save_source_sla_snapshot_and_observability_snapshot(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    sla = pd.DataFrame(
        [
            {
                "source_name": "csv",
                "total_checks": 2,
                "availability_pct": 100,
                "ok_pct": 100,
                "warning_pct": 0,
                "error_pct": 0,
                "missing_pct": 0,
                "stale_pct": 0,
                "avg_age_days": 0.5,
                "max_age_days": 1,
                "latest_status": "OK",
                "last_ok_at": "2026-05-02T10:00:00",
                "days_since_last_ok": 0,
                "reliability_class": "EXCELENTE",
            }
        ]
    )
    summary = {
        "window_days": 30,
        "overall_status": "OK",
        "overall_availability_pct": 100,
        "total_sources": 1,
        "critical_sources": 0,
        "total_alerts": 0,
        "critical_alerts": 0,
        "open_alerts": 0,
        "routine_success_rate_pct": 100,
        "routine_failure_rate_pct": 0,
        "avg_signals_covered_pct": 0.1,
        "coverage_trend_direction": "MELHORANDO",
        "summary_text": "ok",
    }

    sla_rows = save_source_sla_snapshot(db_path, sla, window_days=30)
    snapshot_id = save_operational_observability_snapshot(db_path, summary)
    latest = load_latest_observability_snapshot(db_path)
    history = load_observability_history(db_path)

    assert sla_rows == 1
    assert snapshot_id == 1
    assert latest.loc[0, "overall_status"] == "OK"
    assert history.loc[0, "coverage_trend_direction"] == "MELHORANDO"


def test_observability_store_handles_missing_db(tmp_path):
    db_path = tmp_path / "missing.db"

    assert load_latest_observability_snapshot(db_path).empty
    assert load_observability_history(db_path).empty
