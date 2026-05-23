import pandas as pd

from src.reports.limit_signal_source_report import generate_limit_signal_source_markdown, save_limit_signal_source_markdown
from src.scanners.generate_limit_signal_source_report import main


def test_limit_signal_source_markdown(tmp_path):
    ranked = pd.DataFrame({"variant_id": ["V1"], "variant_robustness_score": [70], "variant_class": ["VARIANT_PROMISING"], "governance_status": ["LIMIT_SOURCE_MORE_TESTING_REQUIRED"]})
    md = generate_limit_signal_source_markdown(ranked)
    assert "# Relatório de Calibração" in md
    path = save_limit_signal_source_markdown(tmp_path / "limit.md", ranked)
    assert path.exists()


def test_generate_limit_signal_source_report_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.generate_limit_signal_source_report.run", lambda **kwargs: {"run_id": 1, "rows": 1, "path": "x.md"})
    assert main(["--run-id", "1"]) == 0
