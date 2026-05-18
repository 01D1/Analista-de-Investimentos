import pandas as pd

from src.reports.paper_fragility_report import generate_paper_fragility_report, save_paper_fragility_report


def test_paper_fragility_report(tmp_path):
    summary = {"status": "COMPLETED", "governance_status": "PAPER_FRAGILITY_OK", "total_trades": 2, "metadata_json": "{}"}
    text = generate_paper_fragility_report(summary, pd.DataFrame({"ticker": ["PETR4"]}), pd.DataFrame({"signal_source": ["quant"]}), pd.DataFrame({"depth": [-0.1]}))
    assert "Relatório de Fragilidade" in text
    assert "Não recomendação" in text
    path = save_paper_fragility_report(tmp_path, summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert path.exists()
