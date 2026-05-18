import pandas as pd

from src.reports.hypothesis_deep_dive_report import generate_hypothesis_deep_dive_markdown, save_hypothesis_deep_dive_markdown
from src.scanners.generate_hypothesis_deep_dive_report import main


def test_hypothesis_deep_dive_markdown(tmp_path):
    deep = pd.DataFrame({"hypothesis_id": ["H1"], "positive_improvement_pct": [0.5], "mean_return_delta": [0], "mean_drawdown_delta": [0], "mean_fragility_delta": [-1], "trades_count": [5], "governance_status": ["HYPOTHESIS_DEEP_MORE_TESTING_REQUIRED"]})
    md = generate_hypothesis_deep_dive_markdown(deep)
    assert "# Relatório Deep Dive de Hipóteses" in md
    path = save_hypothesis_deep_dive_markdown(tmp_path / "deep.md", deep)
    assert path.exists()


def test_generate_hypothesis_deep_dive_report_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.generate_hypothesis_deep_dive_report.run", lambda **kwargs: {"run_id": 1, "rows": 1, "path": "x.md"})
    assert main(["--run-id", "1"]) == 0
