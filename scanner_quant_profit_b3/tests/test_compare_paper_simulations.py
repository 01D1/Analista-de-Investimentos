import pandas as pd

from src.scanners.compare_paper_simulations import main, run


def test_compare_paper_simulations_cli_run(monkeypatch, tmp_path):
    runs = pd.DataFrame({"id": [1, 2], "total_return": [0.0, 0.02], "capital_final": [100000, 102000], "max_drawdown": [-0.1, -0.08], "governance_status": ["PAPER_OBSERVATION_ONLY", "PAPER_ADVANCED_RULES_IMPROVED"]})
    monkeypatch.setattr("src.scanners.compare_paper_simulations.load_paper_simulation_runs", lambda db, limit=5000: runs)
    summary = run(1, 2, db_path=tmp_path / "paper.db")
    assert summary["rows"] > 0
    assert "simulacao" in summary["report"]


def test_compare_paper_simulations_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.compare_paper_simulations.run", lambda *args, **kwargs: {"rows": 1, "saved_rows": 0, "csv_path": "", "report": "ok"})
    assert main(["--simple-run-id", "1", "--advanced-run-id", "2"]) == 0
