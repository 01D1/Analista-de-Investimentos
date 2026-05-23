import pandas as pd

from src.reports.cost_frontier_report import generate_cost_frontier_report


def test_generate_cost_frontier_report_contains_sections():
    results = pd.DataFrame(
        [
            {"variant_id": "A", "variant_type": "exit", "is_efficient": True, "frontier_rank": 1, "tradeoff_score": 80, "tradeoff_class": "TRADEOFF_STRONG", "cost_reduction_pct": 0.2, "return_delta": 0, "drawdown_delta": 0, "turnover_delta": -1, "governance_status": "COST_FRONTIER_OBSERVATION_ONLY"}
        ]
    )

    report = generate_cost_frontier_report(3, results)

    assert "Relatório de Fronteira Custo-Retorno-Drawdown" in report
    assert "Não recomendação" in report
