import pandas as pd

from src.data_quality.ingestion_plan import build_ingestion_plan_from_reconciliation, summarize_ingestion_plan


def test_ingestion_plan_from_b3_reconciliation():
    recon = pd.DataFrame([{"source_domain": "B3_COTAHIST", "issue_type": "DB_MISSING_YEAR", "description": "2026 ausente", "suggested_command": "python -m src.collectors.b3_cotahist_collector --year 2026"}])
    plan = build_ingestion_plan_from_reconciliation(recon)
    summary = summarize_ingestion_plan(plan)
    assert plan.iloc[0]["source_domain"] == "B3"
    assert summary["executable_steps"] == 1


def test_ingestion_plan_profit_options_ri():
    recon = pd.DataFrame(
        [
            {"source_domain": "PROFIT_RTD", "issue_type": "PROFIT_RTD_STALE", "description": "stale", "suggested_command": "python -m src.scanners.realtime_profit_scanner --once --save-db"},
            {"source_domain": "OPTIONS", "issue_type": "NO_CHAIN_SNAPSHOTS", "description": "sem cadeia", "suggested_command": "python -m src.scanners.options_history_builder --save-db --csv"},
            {"source_domain": "RI", "issue_type": "RI_URL_MISSING", "description": "sem url", "suggested_command": ""},
        ]
    )
    plan = build_ingestion_plan_from_reconciliation(recon)
    assert set(plan["source_domain"]) == {"PROFIT_RTD", "OPTIONS", "RI"}
    assert "MANUAL_ACTION" in set(plan["step_type"])

