import pandas as pd

from src.technical.technical_walk_forward import (
    create_technical_walk_forward_windows,
    run_technical_walk_forward,
    summarize_technical_walk_forward,
)


def _bt(rows=180):
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    df = pd.DataFrame(
        {
            "trade_date": dates.astype(str),
            "ticker": ["PETR4", "VALE3"] * (rows // 2),
            "setup_type": "BREAKOUT_VOLUME",
            "setup_score": 75,
            "setup_confidence": 0.7,
            "setup_direction": "BULLISH",
            "technical_score_final": 75,
            "volume_score": 70,
            "trend_score": 70,
            "momentum_score": 70,
            "volatility_score": 50,
            "future_return_5d": [1.0] * (rows // 2) + [-0.2] * (rows - rows // 2),
        }
    )
    return df.sort_values("trade_date").reset_index(drop=True)


def test_create_technical_walk_forward_windows():
    windows = create_technical_walk_forward_windows("2026-01-01", "2026-06-30", 3, 1)
    assert not windows.empty
    assert {"train_start", "test_end"}.issubset(windows.columns)


def test_run_technical_walk_forward_with_synthetic_data():
    backtest = _bt()
    results = run_technical_walk_forward(pd.DataFrame(), pd.DataFrame(), backtest, train_months=2, test_months=1, min_samples_train=10, min_samples_test=5)
    summary = summarize_technical_walk_forward(results)
    assert not results.empty
    assert summary["windows_count"] >= 1
    assert summary["robustness_class"].startswith("TECH_WF_")


def test_run_technical_walk_forward_without_data():
    results = run_technical_walk_forward(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    summary = summarize_technical_walk_forward(results)
    assert results.empty
    assert summary["robustness_class"] == "TECH_WF_DADOS_INSUFICIENTES"

