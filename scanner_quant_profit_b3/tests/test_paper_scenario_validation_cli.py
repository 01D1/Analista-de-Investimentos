from src.scanners.paper_scenario_validation import main, run


def test_paper_scenario_validation_empty_db(tmp_path):
    summary = run(start="2026-01-01", end="2026-04-30", db_path=tmp_path / "empty.db", dry_run=True)
    assert summary["governance_status"] == "PAPER_SCENARIO_BLOCKED_LOW_SAMPLE"


def test_paper_scenario_validation_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.paper_scenario_validation.run", lambda **kwargs: {"status": "PAPER_SCENARIO_BLOCKED_LOW_SAMPLE", "signals_count": 0, "periods_count": 0, "scenarios_count": 0, "mean_return": 0, "positive_periods_pct": 0, "governance_status": "PAPER_SCENARIO_BLOCKED_LOW_SAMPLE", "saved_run_id": None, "csv_paths": {}})
    assert main(["--dry-run"]) == 0
