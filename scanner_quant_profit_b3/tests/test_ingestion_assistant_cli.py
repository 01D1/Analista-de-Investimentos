from src.scanners.ingestion_assistant import run


def test_ingestion_assistant_dry_run(tmp_path):
    db = tmp_path / "assistant.db"
    result = run(sources=["b3"], dry_run=True, save_db=True, csv=False, db_path=db)
    assert result["summary"]["status"] == "DRY_RUN"
    assert result["run_id"] == 1

