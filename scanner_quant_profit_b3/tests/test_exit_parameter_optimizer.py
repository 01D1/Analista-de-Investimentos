import pandas as pd

from src.paper.exit_parameter_optimizer import (
    generate_exit_parameter_report,
    grid_search_exit_parameters,
    rank_exit_parameter_results,
)


def _prices(days=45):
    dates = pd.date_range("2026-01-01", periods=days).astype(str)
    return pd.DataFrame(
        [
            {"trade_date": d, "ticker": "PETR4", "open": 20 + i * 0.1, "high": 21 + i * 0.1, "low": 19 + i * 0.1, "close": 20 + i * 0.1, "volume": 100_000}
            for i, d in enumerate(dates)
        ]
    )


def _signals():
    dates = pd.date_range("2026-01-03", periods=8, freq="5D").astype(str)
    return pd.DataFrame({"trade_date": dates, "ticker": "PETR4", "signal_type": "OBSERVAR", "governance_status": "APPROVED_FOR_STUDY"})


def test_grid_search_exit_parameters_returns_ranked_results():
    grid = {"stop_loss_pct": [0.03], "take_profit_pct": [0.06, 0.10], "trailing_stop_pct": [None], "daily_loss_limit_pct": [None], "atr_stop_multiplier": [None], "max_positions": [2], "risk_pct": [0.005]}
    results = grid_search_exit_parameters(_signals(), _prices(), param_grid=grid, min_trades=1)
    ranked = rank_exit_parameter_results(results)
    assert len(results) == 2
    assert "score_objective" in ranked.columns
    assert "parametro em estudo" in generate_exit_parameter_report(ranked)
