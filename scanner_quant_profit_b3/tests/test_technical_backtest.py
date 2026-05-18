import pandas as pd

from src.technical.technical_backtest import run_technical_setup_backtest, summarize_technical_backtest


def test_technical_backtest_calculates_future_returns():
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    df = pd.DataFrame({"trade_date": dates, "ticker": "PETR4", "close": range(20, 40), "high": range(21, 41), "low": range(19, 39)})
    df["setup_type"] = pd.NA
    df.loc[5, "setup_type"] = "BREAKOUT_VOLUME"
    df["technical_status"] = "TECNICO_PROMISSOR"
    result = run_technical_setup_backtest(df, horizons=[1, 3, 5])
    summary = summarize_technical_backtest(result)
    assert len(result) == 1
    assert result.loc[0, "future_return_5d"] > 0
    assert summary.loc[0, "signals"] == 1

