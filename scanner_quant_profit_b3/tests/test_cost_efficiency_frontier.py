import pandas as pd

from src.paper.cost_efficiency_frontier import calculate_cost_efficiency_frontier, summarize_efficiency_frontier


def test_calculate_cost_efficiency_frontier_marks_dominated_variant():
    variants = pd.DataFrame(
        [
            {"variant_id": "A", "cost_reduction_pct": 0.3, "return_delta": 0.02, "drawdown_delta": 0.01, "turnover_delta": -10, "efficiency_score": 90},
            {"variant_id": "B", "cost_reduction_pct": 0.1, "return_delta": 0.01, "drawdown_delta": 0.0, "turnover_delta": 0, "efficiency_score": 50},
        ]
    )

    out = calculate_cost_efficiency_frontier(variants)
    summary = summarize_efficiency_frontier(out)

    assert out.loc[out["variant_id"] == "A", "is_efficient"].iloc[0]
    assert not out.loc[out["variant_id"] == "B", "is_efficient"].iloc[0]
    assert summary["efficient_count"] == 1
