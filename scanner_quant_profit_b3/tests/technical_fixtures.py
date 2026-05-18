import pandas as pd


def sample_price_df(rows: int = 80) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series(range(10, 10 + rows), dtype=float)
    volume = pd.Series([1000.0] * rows)
    volume.iloc[-1] = 3000
    close.iloc[-1] = close.iloc[-2] + 5
    return pd.DataFrame(
        {
            "trade_date": dates.astype(str),
            "ticker": "PETR4",
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": volume,
            "trades": 100,
            "quantity": volume,
        }
    )

