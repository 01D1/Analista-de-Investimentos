import pandas as pd

from src.paper.cost_return_tradeoff import calculate_tradeoff_metrics


def test_calculate_tradeoff_metrics_classifies_efficient_and_bad():
    variants = pd.DataFrame(
        [
            {"variant_id": "A", "variant_type": "exit", "cost_reduction_pct": 0.2, "return_delta": 0.01, "drawdown_delta": 0.01, "turnover_delta": -10, "trades_count": 10},
            {"variant_id": "B", "variant_type": "exit", "cost_reduction_pct": 0.2, "return_delta": -0.05, "drawdown_delta": -0.05, "turnover_delta": 10, "trades_count": 10},
        ]
    )

    out = calculate_tradeoff_metrics(variants)

    assert out.loc[out["variant_id"] == "A", "tradeoff_class"].iloc[0] == "EFFICIENT_TRADEOFF"
    assert out.loc[out["variant_id"] == "B", "tradeoff_class"].iloc[0] == "BAD_TRADEOFF"
    assert "efficiency_score" in out.columns
