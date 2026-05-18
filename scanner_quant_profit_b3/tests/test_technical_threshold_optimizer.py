import pandas as pd

from src.technical.technical_threshold_optimizer import grid_search_technical_thresholds, rank_technical_threshold_results


def test_grid_search_technical_thresholds_ranks_results():
    df = pd.DataFrame(
        {
            "ticker": ["PETR4"] * 120,
            "setup_type": ["BREAKOUT_VOLUME"] * 120,
            "setup_direction": ["BULLISH"] * 120,
            "technical_score_final": [80] * 120,
            "setup_score": [75] * 120,
            "setup_confidence": [0.8] * 120,
            "volume_score": [70] * 120,
            "trend_score": [70] * 120,
            "momentum_score": [70] * 120,
            "future_return_1d": [0.1] * 120,
            "future_return_3d": [0.2] * 120,
            "future_return_5d": [0.5] * 120,
            "future_return_10d": [1.0] * 120,
        }
    )
    results = grid_search_technical_thresholds(df, param_grid={"min_technical_score": [70], "min_setup_score": [70]}, min_samples=50)
    ranked = rank_technical_threshold_results(results)
    assert ranked.loc[0, "signals_count"] == 120
    assert ranked.loc[0, "mean_return_5d"] == 0.5

