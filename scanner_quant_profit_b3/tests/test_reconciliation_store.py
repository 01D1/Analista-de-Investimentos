import pandas as pd

from src.data_quality.reconciliation_store import load_latest_reconciliation_results, save_reconciliation_run


def test_save_reconciliation_run(tmp_path):
    db = tmp_path / "recon.db"
    results = pd.DataFrame(
        [
            {
                "source_domain": "B3_COTAHIST",
                "issue_type": "RAW_PRESENT_DB_EMPTY",
                "severity": "CRITICAL",
                "status": "OPEN",
                "description": "raw sem banco",
                "suggested_command": "python -m src.collectors.b3_cotahist_collector --year 2026",
                "executed": False,
                "execution_status": "NOT_EXECUTED",
                "metadata_json": "{}",
            }
        ]
    )
    run_id = save_reconciliation_run(db, {"reconciliation_type": "b3", "status": "WARNING", "issues_count": 1}, results)
    loaded = load_latest_reconciliation_results(db, "b3")
    assert run_id == 1
    assert loaded.iloc[0]["issue_type"] == "RAW_PRESENT_DB_EMPTY"

