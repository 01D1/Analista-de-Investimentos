import pandas as pd

from src.reports.paper_rules_robustness_report import generate_paper_rules_robustness_report, save_paper_rules_robustness_report


def test_paper_rules_robustness_report_markdown(tmp_path):
    comparison = pd.DataFrame({"metric": ["total_return"], "simple_value": [0], "advanced_value": [0.01]})
    opt = pd.DataFrame({"params_json": ['{"stop_loss_pct": 0.03}'], "total_return": [0.01]})
    wf = pd.DataFrame({"window_id": [1], "test_return": [0.01]})
    text = generate_paper_rules_robustness_report(comparison, opt, wf, {"windows_count": 1, "robustness_class": "PAPER_WF_DADOS_INSUFICIENTES"}, {"governance_status": "PAPER_OOS_BLOCKED_DATA"})
    assert "Relatorio de Robustez" in text
    assert "Nao recomendacao" in text
    path = save_paper_rules_robustness_report(tmp_path, comparison, opt, wf)
    assert path.exists()
