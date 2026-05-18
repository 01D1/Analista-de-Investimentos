import pandas as pd

from src.paper.signal_source_validation import compare_signal_sources


def test_compare_signal_sources():
    results = pd.DataFrame(
        {
            "signal_source": ["quant", "quant", "technical"],
            "total_return": [0.02, 0.01, -0.01],
            "max_drawdown": [-0.02, -0.03, -0.05],
            "win_rate": [0.6, 0.7, 0.4],
            "profit_factor": [1.5, 1.4, 0.8],
            "turnover": [20, 22, 3],
            "trades_count": [20, 22, 3],
        }
    )
    out = compare_signal_sources(results)
    assert "quant" in out["signal_source"].tolist()
    assert "robustness_class" in out.columns
