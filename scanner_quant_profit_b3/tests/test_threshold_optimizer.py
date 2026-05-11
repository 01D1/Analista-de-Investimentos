import pandas as pd

from src.quant.threshold_optimizer import (
    generate_threshold_report,
    grid_search_thresholds,
    rank_threshold_results,
)


def _backtest():
    return pd.DataFrame(
        [
            {
                "ticker": "A",
                "signal_type": "FORÇA COM LIQUIDEZ",
                "score_final": 90,
                "score_liquidez": 90,
                "score_risco": 80,
                "execution_quality": "EXCELENTE",
                "net_return_5d": 1.0,
                "net_return_3d": 0.8,
                "mae_5d": -0.5,
            },
            {
                "ticker": "B",
                "signal_type": "OBSERVAR",
                "score_final": 60,
                "score_liquidez": 50,
                "score_risco": 60,
                "execution_quality": "ACEITAVEL",
                "net_return_5d": -0.5,
                "net_return_3d": -0.2,
                "mae_5d": -2.0,
            },
            {
                "ticker": "C",
                "signal_type": "SEM ASSIMETRIA",
                "score_final": 30,
                "score_liquidez": 20,
                "score_risco": 40,
                "execution_quality": "INVIAVEL",
                "net_return_5d": -1.5,
                "net_return_3d": -1.0,
                "mae_5d": -4.0,
            },
        ]
    )


def test_grid_search_thresholds_returns_candidate_metrics():
    results = grid_search_thresholds(
        _backtest(),
        {
            "score_final_min": [0, 80],
            "score_liquidez_min": [0, 70],
            "allowed_execution_quality": [["EXCELENTE", "BOA", "ACEITAVEL"], ["EXCELENTE"]],
        },
        min_samples=1,
    )

    assert not results.empty
    assert "mean_net_return_5d" in results.columns
    assert results["samples"].max() == 3


def test_rank_threshold_results_prioritizes_positive_net_return():
    results = grid_search_thresholds(
        _backtest(),
        {"score_final_min": [0, 80], "score_liquidez_min": [0, 70]},
        min_samples=1,
    )
    ranked = rank_threshold_results(results)
    report = generate_threshold_report(ranked)

    assert ranked.iloc[0]["mean_net_return_5d"] >= ranked.iloc[-1]["mean_net_return_5d"]
    assert "melhores thresholds" in report
