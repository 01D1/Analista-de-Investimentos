import pandas as pd

from src.paper.hypothesis_asset_decomposition import decompose_hypothesis_by_asset


def test_decompose_hypothesis_by_asset_classifies_hurting_asset():
    deep = pd.DataFrame(
        {
            "hypothesis_id": ["H1", "H1"],
            "ticker": ["PETR4", "TODOS"],
            "trades_count": [10, 20],
            "mean_return_delta": [-0.01, -0.005],
            "mean_drawdown_delta": [0.0, 0.0],
            "mean_fragility_delta": [2.0, 1.0],
            "positive_improvement_pct": [0.1, 0.2],
            "cost_sensitivity_flag": [False, False],
            "slippage_sensitivity_flag": [False, False],
            "block_reason": ["BLOCKED_BY_NEGATIVE_RETURN", "BLOCKED_BY_NEGATIVE_RETURN"],
        }
    )
    out = decompose_hypothesis_by_asset(deep)
    assert out.loc[0, "asset_classification"] == "ASSET_HURTS_HYPOTHESIS"
