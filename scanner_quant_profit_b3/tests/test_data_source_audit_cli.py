from src.scanners.data_source_audit import run


def test_data_source_audit_cli_synthetic(tmp_path):
    db = tmp_path / "audit_cli.db"
    result = run(sources=["b3"], save_db=True, csv=False, db_path=db)
    assert result["summary"]["sources_checked"] == 1
    assert "results" in result

