import pandas as pd

from src.reports.ingestion_assistant_report import generate_ingestion_assistant_report


def test_ingestion_assistant_report_markdown():
    report = generate_ingestion_assistant_report({"status": "DRY_RUN", "sources": "b3", "steps_total": 1}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert "# Relatório do Assistente de Ingestão" in report

