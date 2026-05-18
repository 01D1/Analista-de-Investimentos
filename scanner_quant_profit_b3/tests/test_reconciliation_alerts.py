import pandas as pd

from src.data_quality.reconciliation_alerts import build_alerts_from_reconciliation


def test_reconciliation_alerts_for_b3_db_empty():
    results = pd.DataFrame(
        [
            {
                "source_domain": "B3_COTAHIST",
                "issue_type": "RAW_PRESENT_DB_EMPTY",
                "severity": "CRITICAL",
                "status": "OPEN",
                "description": "raw sem banco",
                "suggested_command": "",
                "executed": False,
                "execution_status": "NOT_EXECUTED",
                "metadata_json": "{}",
            }
        ]
    )
    alerts = build_alerts_from_reconciliation(results)
    assert alerts.iloc[0]["alert_type"] == "B3_DB_EMPTY"

