import pandas as pd

from src.paper.hypothesis_ranking import generate_hypothesis_ranking_report, rank_hypotheses


def test_rank_hypotheses_scores_and_report():
    validation = pd.DataFrame(
        [
            {
                "hypothesis_id": "H1",
                "signal_source": "quant",
                "scenario_name": "BASE",
                "windows_count": 2,
                "useful_cells": 2,
                "positive_improvement_pct": 0.8,
                "mean_return_delta": 0.002,
                "mean_drawdown_delta": 0.01,
                "mean_fragility_delta": -10,
                "mean_cost_drag_delta": -1,
                "overfitting_flag": False,
                "cost_sensitivity_flag": False,
                "regime_instability_flag": False,
                "data_coverage_status": "COVERAGE_USEFUL",
            },
            {
                "hypothesis_id": "H1",
                "signal_source": "technical",
                "scenario_name": "BASE",
                "windows_count": 2,
                "useful_cells": 2,
                "positive_improvement_pct": 0.7,
                "mean_return_delta": 0.001,
                "mean_drawdown_delta": 0.005,
                "mean_fragility_delta": -5,
                "mean_cost_drag_delta": -1,
                "overfitting_flag": False,
                "cost_sensitivity_flag": False,
                "regime_instability_flag": False,
                "data_coverage_status": "COVERAGE_USEFUL",
            },
        ]
    )
    ranked = rank_hypotheses(validation)
    assert ranked.loc[0, "hypothesis_id"] == "H1"
    assert ranked.loc[0, "useful_sources_count"] == 2
    assert "H1" in generate_hypothesis_ranking_report(ranked)

