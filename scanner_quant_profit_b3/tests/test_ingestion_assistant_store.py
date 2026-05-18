import pandas as pd

from src.data_quality.ingestion_assistant_store import load_ingestion_assistant_runs, save_ingestion_assistant_run


def test_save_ingestion_assistant_run(tmp_path):
    db = tmp_path / "ingestion.db"
    steps = pd.DataFrame([{"step_id": "B3_001", "step_order": 1, "source_domain": "B3", "step_type": "CHECK", "title": "Check", "suggested_command": "", "can_execute": False, "requires_confirm": False, "risk_level": "LOW", "status": "MANUAL_REQUIRED", "stdout": "", "stderr": "", "metadata_json": "{}"}])
    run_id = save_ingestion_assistant_run(db, {"status": "DRY_RUN", "dry_run": True, "sources": "b3", "steps_total": 1, "manual_steps": 1}, steps)
    loaded = load_ingestion_assistant_runs(db)
    assert run_id == 1
    assert loaded.iloc[0]["status"] == "DRY_RUN"

