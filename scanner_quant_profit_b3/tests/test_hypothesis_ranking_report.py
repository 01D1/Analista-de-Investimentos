import pandas as pd

from src.reports.hypothesis_ranking_report import generate_hypothesis_ranking_markdown, save_hypothesis_ranking_markdown
from src.scanners.generate_hypothesis_ranking_report import main


def test_hypothesis_ranking_markdown(tmp_path):
    ranked = pd.DataFrame(
        {
            "hypothesis_id": ["H1"],
            "hypothesis_robustness_score": [75],
            "hypothesis_class": ["HYPOTHESIS_ROBUST"],
            "governance_status": ["HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION"],
            "useful_sources_count": [2],
            "mean_return_delta": [0.01],
            "mean_drawdown_delta": [0.01],
            "mean_fragility_delta": [-5],
            "cost_sensitivity_flag": [False],
            "overfitting_flag": [False],
        }
    )
    md = generate_hypothesis_ranking_markdown(ranked)
    assert "# Relatório de Ranking de Hipóteses" in md
    path = save_hypothesis_ranking_markdown(tmp_path / "report.md", ranked)
    assert path.exists()


def test_generate_hypothesis_ranking_report_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.generate_hypothesis_ranking_report.run", lambda **kwargs: {"run_id": 1, "rows": 1, "path": "x.md"})
    assert main(["--run-id", "1"]) == 0

