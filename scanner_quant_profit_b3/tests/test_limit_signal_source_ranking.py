import pandas as pd

from src.paper.limit_signal_source_ranking import generate_limit_signal_source_ranking_report, rank_limit_signal_source_variants


def test_rank_limit_signal_source_variants_scores_best():
    oos = pd.DataFrame(
        {
            "variant_id": ["V1"],
            "signal_source": ["quant"],
            "regime": ["SEM_REGIME"],
            "coverage_status": ["COVERAGE_USEFUL"],
            "positive_improvement_pct": [0.8],
            "mean_return_delta": [0.001],
            "mean_drawdown_delta": [0.0],
            "mean_fragility_delta": [-3],
            "mean_cost_drag_delta": [-1],
            "mean_slippage_delta": [-1],
            "trades_count": [100],
            "removed_pct": [0.2],
            "cost_sensitivity_flag": [False],
            "slippage_sensitivity_flag": [False],
            "overfitting_flag": [False],
            "low_sample_flag": [False],
        }
    )
    ranked = rank_limit_signal_source_variants(oos)
    assert ranked.loc[0, "variant_id"] == "V1"
    assert "V1" in generate_limit_signal_source_ranking_report(ranked)

