from src.db.init_db import init_database
from src.scanners.signal_coverage_check import main, run


def test_signal_coverage_check_run_saves(tmp_path):
    db = tmp_path / "coverage_cli.db"
    init_database(db, verbose=False)
    result = run(start="2026-01-02", end="2026-01-31", sources=["quant", "technical"], save_db=True, db_path=db)
    assert result["saved_run_id"] == 1
    assert {"quant", "technical"} == set(result["coverage"]["signal_source"])


def test_signal_coverage_check_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.signal_coverage_check.run", lambda **kwargs: {"coverage": None, "report": "ok", "saved_run_id": None, "csv_path": ""})
    assert main(["--start", "2026-01-02", "--end", "2026-01-31"]) == 0

