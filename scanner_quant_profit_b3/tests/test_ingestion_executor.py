import pandas as pd

from src.data_quality.ingestion_executor import execute_ingestion_plan, execute_ingestion_step


def _step(command="python -m src.scanners.data_source_audit --csv", can_execute=True):
    return {
        "step_id": "S1",
        "step_order": 1,
        "source_domain": "B3",
        "step_type": "CHECK",
        "title": "check",
        "description": "",
        "suggested_command": command,
        "can_execute": can_execute,
        "requires_confirm": True,
        "risk_level": "LOW",
        "metadata_json": "{}",
    }


def test_dry_run_does_not_execute():
    result = execute_ingestion_step(_step(), dry_run=True, confirm=False)
    assert result["status"] == "DRY_RUN"


def test_execute_without_confirm_blocks():
    result = execute_ingestion_step(_step(), dry_run=False, confirm=False)
    assert result["status"] == "BLOCKED_CONFIRMATION_REQUIRED"


def test_non_whitelisted_blocks():
    result = execute_ingestion_step(_step("python -m os"), dry_run=False, confirm=True)
    assert result["status"] == "BLOCKED_NOT_WHITELISTED"


def test_manual_step_required():
    result = execute_ingestion_plan(pd.DataFrame([_step("", False)]), dry_run=True)
    assert result.iloc[0]["status"] == "MANUAL_REQUIRED"

