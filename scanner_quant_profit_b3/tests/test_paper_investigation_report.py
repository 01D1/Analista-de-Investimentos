import pandas as pd

from src.reports.paper_investigation_report import generate_paper_investigation_report


def test_paper_investigation_report_markdown():
    report = generate_paper_investigation_report(
        {"base_paper_run_id": 2, "base_fragility_run_id": 1, "hypotheses_count": 1, "best_hypothesis_id": "EXCLUDE_ASSET_ITUB4"},
        pd.DataFrame({"hypothesis_id": ["EXCLUDE_ASSET_ITUB4"], "title": ["Investigar exclusao"], "hypothesis_type": ["EXCLUDE_ASSET"], "target": ["ITUB4"]}),
        pd.DataFrame({"hypothesis_id": ["EXCLUDE_ASSET_ITUB4"], "simulated_return": [0.02], "simulated_drawdown": [-0.05], "simulated_trades": [30], "fragility_score_after": [20], "improvement_score": [40], "governance_status": ["INVESTIGATION_APPROVED_FOR_FURTHER_TEST"], "metadata_json": ["{}"]}),
    )
    assert "# Relatorio de Investigacoes" in report
    assert "Nao recomendacao" in report
