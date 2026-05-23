import pandas as pd

from src.reports.cost_reduction_report import generate_cost_reduction_report


def test_generate_cost_reduction_report_contains_non_recommendation():
    results = pd.DataFrame(
        [
            {"variant_id": "DISABLE_REBALANCE", "variant_type": "rebalance", "cost_reduction": 10, "return_delta": 0, "drawdown_delta": 0, "turnover_delta": -1, "governance_status": "COST_REDUCTION_OBSERVATION_ONLY", "improvement_score": 60}
        ]
    )

    report = generate_cost_reduction_report(2, results)

    assert "Relatório de Simulação de Redução de Custos" in report
    assert "Não recomendação" in report
