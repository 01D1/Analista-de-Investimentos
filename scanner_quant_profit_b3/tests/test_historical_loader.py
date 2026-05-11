import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.quant.historical_loader import detect_available_price_tables, load_daily_prices


def test_load_daily_prices_returns_empty_frame_for_empty_database(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)

    prices = load_daily_prices(db_path)

    assert prices.empty
    assert set(prices.columns) >= {
        "trade_date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trades",
        "quantity",
    }
    assert "mensagem" in prices.attrs


def test_detect_available_price_tables_reports_schema(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)

    tables = detect_available_price_tables(db_path)

    cotahist = next(item for item in tables if item["table"] == "cotahist_daily")
    assert "ticker" in cotahist["columns"]
    assert "close" in cotahist["columns"]
    assert cotahist["usable"] is True


def test_load_daily_prices_reads_cotahist_daily_with_filters(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    rows = pd.DataFrame(
        [
            {
                "trade_date": "2026-01-02",
                "ticker": "PETR4",
                "market_type": "010",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.8,
                "volume": 1000000.0,
                "trades": 1000,
                "quantity": 100000,
            },
            {
                "trade_date": "2026-01-03",
                "ticker": "VALE3",
                "market_type": "010",
                "open": 20.0,
                "high": 21.0,
                "low": 19.5,
                "close": 20.5,
                "volume": 2000000.0,
                "trades": 2000,
                "quantity": 200000,
            },
        ]
    )
    with sqlite3.connect(db_path) as con:
        rows.to_sql("cotahist_daily", con, if_exists="append", index=False)

    prices = load_daily_prices(db_path, tickers=["PETR4"], start_date="2026-01-01", end_date="2026-01-02")

    assert prices["ticker"].tolist() == ["PETR4"]
    assert prices["trade_date"].tolist() == ["2026-01-02"]
    assert prices["close"].iloc[0] == 10.8
