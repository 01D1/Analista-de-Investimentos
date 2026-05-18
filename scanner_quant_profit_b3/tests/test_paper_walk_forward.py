import pandas as pd

from src.paper.paper_walk_forward import (
    create_paper_walk_forward_windows,
    run_paper_walk_forward,
    summarize_paper_walk_forward,
)


def _prices(days=120):
    dates = pd.date_range("2026-01-01", periods=days).astype(str)
    rows = []
    for i, date in enumerate(dates):
        price = 20 + i * 0.05
        rows.append({"trade_date": date, "ticker": "PETR4", "open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 100_000})
    return pd.DataFrame(rows)


def _signals():
    dates = pd.date_range("2026-01-05", periods=20, freq="5D").astype(str)
    return pd.DataFrame({"trade_date": dates, "ticker": "PETR4", "signal_type": "OBSERVAR", "governance_status": "APPROVED_FOR_STUDY"})


def test_create_paper_walk_forward_windows():
    windows = create_paper_walk_forward_windows("2026-01-01", "2026-04-30", train_months=2, test_months=1)
    assert not windows.empty
    assert {"train_start", "test_end"}.issubset(windows.columns)


def test_run_paper_walk_forward_with_synthetic_data():
    grid = {"stop_loss_pct": [0.03], "take_profit_pct": [0.06], "trailing_stop_pct": [None], "daily_loss_limit_pct": [None], "atr_stop_multiplier": [None], "max_positions": [2], "risk_pct": [0.005]}
    results = run_paper_walk_forward(_signals(), _prices(), train_months=2, test_months=1, param_grid=grid)
    summary = summarize_paper_walk_forward(results)
    assert "robustness_class" in summary
    assert "test_return" in results.columns


def test_run_paper_walk_forward_without_prices_is_empty():
    results = run_paper_walk_forward(pd.DataFrame(), pd.DataFrame())
    assert results.empty
    assert summarize_paper_walk_forward(results)["robustness_class"] == "PAPER_WF_DADOS_INSUFICIENTES"
