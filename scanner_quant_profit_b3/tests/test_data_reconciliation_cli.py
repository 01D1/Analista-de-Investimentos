from src.scanners.data_reconciliation import run


def test_data_reconciliation_cli_dry_run(tmp_path):
    db = tmp_path / "recon_cli.db"
    result = run(sources=["b3"], save_db=True, csv=False, db_path=db)
    assert result["summary"]["issues_count"] >= 0
    assert "results" in result

