import pandas as pd

from src.ops.retention_store import (
    load_retention_cleanup_details,
    load_retention_cleanup_runs,
    save_retention_cleanup_run,
)


def test_retention_store_saves_run_and_details(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    summary = {
        "started_at": "2026-05-01T10:00:00",
        "finished_at": "2026-05-01T10:01:00",
        "dry_run": 1,
        "status": "DRY_RUN",
        "tables_evaluated": 1,
        "rows_candidates": 5,
        "rows_archived": 0,
        "rows_deleted": 0,
        "archive_dir": "data/archive",
        "warnings_count": 0,
        "errors_count": 0,
    }
    details = pd.DataFrame(
        [
            {
                "table_name": "source_health_checks",
                "cutoff_date": "2026-01-01",
                "rows_total": 10,
                "rows_to_delete": 5,
                "rows_archived": 0,
                "rows_deleted": 0,
                "protected": 0,
                "status": "DRY_RUN",
                "archive_path": "",
                "message": "Dry-run",
            }
        ]
    )

    run_id = save_retention_cleanup_run(db_path, summary, details)
    runs = load_retention_cleanup_runs(db_path)
    loaded_details = load_retention_cleanup_details(db_path, run_id)

    assert run_id == 1
    assert runs.loc[0, "rows_candidates"] == 5
    assert loaded_details.loc[0, "table_name"] == "source_health_checks"
