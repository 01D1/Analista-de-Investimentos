import pandas as pd

from src.reports.paper_scenario_validation_report import generate_paper_scenario_validation_report, save_paper_scenario_validation_report


def test_paper_scenario_validation_report(tmp_path):
    run = {"status": "COMPLETED", "governance_status": "PAPER_SCENARIO_PROMISING", "periods_count": 2, "scenarios_count": 3, "metadata_json": "{}"}
    text = generate_paper_scenario_validation_report(run, pd.DataFrame({"period_id": [1]}), pd.DataFrame({"cost_scenario": ["COST_BASE"]}), pd.DataFrame({"signal_source": ["quant"]}))
    assert "Relatorio de Validacao Multi-Cenario" in text
    assert "Nao Recomendacao" in text
    path = save_paper_scenario_validation_report(tmp_path, run)
    assert path.exists()
