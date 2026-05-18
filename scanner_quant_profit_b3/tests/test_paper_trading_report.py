import pandas as pd

from src.reports.paper_trading_report import generate_paper_trading_report, save_paper_trading_report


def test_paper_trading_report_markdown(tmp_path):
    summary = {"status": "COMPLETED", "governance_status": "PAPER_OBSERVATION_ONLY", "capital_initial": 100000, "capital_final": 100500}
    exits = pd.DataFrame({"exit_rule_triggered": ["STOP_LOSS_PCT"]})
    text = generate_paper_trading_report(summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), exits)
    assert "Relatório de Paper Trading" in text
    assert "Regras de Saída" in text
    assert "Não recomendação" in text
    path = save_paper_trading_report(summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), tmp_path, exits)
    assert path.exists()
