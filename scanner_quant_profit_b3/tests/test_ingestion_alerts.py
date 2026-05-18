import pandas as pd

from src.data_quality.ingestion_alerts import build_alerts_from_ingestion_run


def test_ingestion_alerts_failed_step_and_no_improvement():
    steps = pd.DataFrame([{"status": "FAILED", "title": "Falha", "source_domain": "B3"}])
    validation = pd.DataFrame([{"source_domain": "OPTIONS", "validation_status": "FAILED", "message": "sem opcoes"}])
    comparison = pd.DataFrame([{"score_delta": 0}])
    alerts = build_alerts_from_ingestion_run({}, steps, validation, comparison)
    assert {"INGESTION_STEP_FAILED", "INGESTION_OPTIONS_STILL_MISSING", "INGESTION_NO_IMPROVEMENT"}.issubset(set(alerts["alert_type"]))

