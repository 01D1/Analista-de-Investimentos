import pandas as pd

from src.paper.hypothesis_signal_source_decomposition import decompose_hypothesis_by_signal_source


def test_decompose_hypothesis_by_signal_source_classifies_support():
    deep = pd.DataFrame(
        {
            "hypothesis_id": ["H1"],
            "signal_source": ["quant"],
            "trades_count": [12],
            "data_coverage_status": ["COVERAGE_USEFUL"],
            "mean_return_delta": [0.01],
            "mean_drawdown_delta": [0.0],
            "mean_fragility_delta": [-5.0],
            "positive_improvement_pct": [0.8],
            "block_reason": ["NO_CLEAR_BLOCKER"],
        }
    )
    out = decompose_hypothesis_by_signal_source(deep)
    assert out.loc[0, "source_classification"] == "SOURCE_SUPPORTS_HYPOTHESIS"
