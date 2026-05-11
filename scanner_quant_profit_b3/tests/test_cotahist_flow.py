"""Cobertura do fluxo COTAHIST -> cotahist_daily -> b3_quotes."""
import sqlite3

import pandas as pd

from src.collectors.b3_cotahist_collector import parse_cotahist_txt, save_cotahist_daily
from src.db.init_db import init_database
from src.strategies.call_continuity_strategy import get_options, get_stock_history


def _cotahist_line(
    *,
    trade_date: str,
    ticker: str,
    market_type: str,
    company_name: str = "EMPRESA",
    open_price: int = 3500,
    high_price: int = 3600,
    low_price: int = 3400,
    avg_price: int = 3550,
    close_price: int = 3580,
    trades: int = 123,
    quantity: int = 10000,
    volume: int = 35800000,
    strike: int = 3500,
    expiration_date: str = "20260620",
) -> str:
    line = [" "] * 245

    def put(start: int, end: int, value: str) -> None:
        width = end - start
        line[start:end] = f"{value:<{width}}"[:width]

    def put_num(start: int, end: int, value: int) -> None:
        width = end - start
        line[start:end] = f"{value:0{width}d}"[-width:]

    put(0, 2, "01")
    put(2, 10, trade_date)
    put(10, 12, "02")
    put(12, 24, ticker)
    put(24, 27, market_type)
    put(27, 39, company_name)
    put(39, 49, "ON")
    put(49, 52, "")
    put_num(56, 69, open_price)
    put_num(69, 82, high_price)
    put_num(82, 95, low_price)
    put_num(95, 108, avg_price)
    put_num(108, 121, close_price)
    put_num(121, 134, close_price - 1)
    put_num(134, 147, close_price + 1)
    put_num(147, 152, trades)
    put_num(152, 170, quantity)
    put_num(170, 188, volume)
    put_num(188, 201, strike)
    put(202, 210, expiration_date)
    return "".join(line) + "\n"


def test_parse_cotahist_filters_assets_and_maps_schema(tmp_path):
    txt_path = tmp_path / "COTAHIST_A2026.TXT"
    txt_path.write_text(
        "".join(
            [
                _cotahist_line(trade_date="20260504", ticker="PETR4", market_type="010"),
                _cotahist_line(trade_date="20260504", ticker="PETRF350", market_type="070"),
                _cotahist_line(trade_date="20260504", ticker="VALE3", market_type="010"),
            ]
        ),
        encoding="latin-1",
    )

    df = parse_cotahist_txt(txt_path, source_year=2026, ativos_base=["PETR4"])

    assert set(df["ticker"]) == {"PETR4", "PETRF350"}
    assert set(df.columns).issuperset(
        {
            "trade_date",
            "ticker",
            "market_type",
            "close",
            "strike",
            "option_type",
            "expiration_date",
            "source_year",
        }
    )
    assert df.loc[df["ticker"] == "PETRF350", "option_type"].iloc[0] == "CALL"
    assert df.loc[df["ticker"] == "PETR4", "option_type"].isna().iloc[0]


def test_cotahist_daily_feeds_legacy_b3_quotes_view(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)

    df = pd.DataFrame(
        [
            {
                "trade_date": "2026-05-04",
                "ticker": "PETR4",
                "market_type": "010",
                "bdi_code": "02",
                "company_name": "PETROBRAS",
                "specification": "ON",
                "term_days": "",
                "open": 35.0,
                "high": 36.0,
                "low": 34.0,
                "average": 35.5,
                "close": 35.8,
                "best_bid": 35.7,
                "best_ask": 35.9,
                "trades": 1000,
                "quantity": 100000,
                "volume": 3580000.0,
                "strike": 0.0,
                "option_type": None,
                "expiration_date": None,
                "source_year": 2026,
            },
            {
                "trade_date": "2026-05-04",
                "ticker": "PETRF350",
                "market_type": "070",
                "bdi_code": "78",
                "company_name": "PETROBRAS",
                "specification": "ON",
                "term_days": "",
                "open": 1.8,
                "high": 2.0,
                "low": 1.7,
                "average": 1.9,
                "close": 1.95,
                "best_bid": 1.94,
                "best_ask": 1.96,
                "trades": 150,
                "quantity": 15000,
                "volume": 300000.0,
                "strike": 35.0,
                "option_type": "CALL",
                "expiration_date": "2026-06-20",
                "source_year": 2026,
            },
        ]
    )

    save_cotahist_daily(df, db_path, source_year=2026)

    with sqlite3.connect(db_path) as con:
        view_df = pd.read_sql_query(
            "SELECT ticker, asset_type, option_exercise_price, option_maturity FROM b3_quotes ORDER BY ticker",
            con,
        )
        stock_history = get_stock_history(con, "PETR4")
        options = get_options(con, "PETR4", "CALL", min_dte=1, max_dte=90)

    assert view_df["asset_type"].tolist() == ["ACAO", "CALL"]
    assert view_df.loc[view_df["ticker"] == "PETRF350", "option_exercise_price"].iloc[0] == 35.0
    assert view_df.loc[view_df["ticker"] == "PETRF350", "option_maturity"].iloc[0] == "2026-06-20"
    assert not stock_history.empty
    assert stock_history["close"].iloc[-1] == 35.8
    assert not options.empty
    assert options["ticker"].iloc[0] == "PETRF350"
