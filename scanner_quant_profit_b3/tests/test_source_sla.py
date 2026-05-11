import pandas as pd

from src.context.source_sla import calculate_overall_sla, calculate_source_sla


def test_source_sla_classifies_excellent_source():
    history = pd.DataFrame(
        [
            {"checked_at": "2026-05-01T10:00:00", "source_name": "csv", "status": "OK", "available": 1, "age_days": 0, "latest_date": "2026-05-01"},
            {"checked_at": "2026-05-02T10:00:00", "source_name": "csv", "status": "OK", "available": 1, "age_days": 1, "latest_date": "2026-05-02"},
        ]
    )

    sla = calculate_source_sla(history, window_days=30)

    assert sla.loc[0, "availability_pct"] == 100
    assert sla.loc[0, "reliability_class"] == "EXCELENTE"


def test_source_sla_classifies_critical_source():
    history = pd.DataFrame(
        [
            {"checked_at": "2026-05-01T10:00:00", "source_name": "news", "status": "MISSING", "available": 0, "age_days": None},
            {"checked_at": "2026-05-02T10:00:00", "source_name": "news", "status": "ERROR", "available": 0, "age_days": None},
        ]
    )

    sla = calculate_source_sla(history, window_days=30)
    overall = calculate_overall_sla(sla)

    assert sla.loc[0, "reliability_class"] == "CRITICA"
    assert overall["overall_status"] == "CRITICAL"


def test_source_sla_handles_empty_history():
    sla = calculate_source_sla(pd.DataFrame())
    overall = calculate_overall_sla(sla)

    assert sla.empty
    assert overall["overall_status"] == "NO_DATA"
