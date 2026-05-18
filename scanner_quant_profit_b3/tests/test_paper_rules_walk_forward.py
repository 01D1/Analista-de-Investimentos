import pandas as pd

from src.scanners.paper_rules_walk_forward import main, run


def test_paper_rules_walk_forward_run_dry_with_empty_db(tmp_path):
    summary = run(start="2026-01-01", end="2026-04-30", db_path=tmp_path / "empty.db", dry_run=True)
    assert summary["status"] == "PAPER_WF_DADOS_INSUFICIENTES"


def test_paper_rules_walk_forward_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.paper_rules_walk_forward.run", lambda **kwargs: {"status": "PAPER_WF_DADOS_INSUFICIENTES", "signals_count": 0, "windows_count": 0, "positive_windows_pct": 0, "mean_test_return": 0, "robustness_class": "PAPER_WF_DADOS_INSUFICIENTES", "governance_status": "PAPER_OOS_BLOCKED_DATA", "saved_run_id": None, "csv_paths": {}})
    assert main(["--dry-run"]) == 0
