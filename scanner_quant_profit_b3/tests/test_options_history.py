import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.options.options_history import (
    create_daily_chain_view,
    get_available_option_history_range,
    get_chain_for_date,
    load_options_chain_snapshots,
)


def _insert_snapshot(con, trade_date, captured_at, ticker="PETRA300", price=1.0):
    con.execute(
        """
        INSERT INTO options_chain_snapshots (
            trade_date, captured_at, option_ticker, underlying, option_type, strike,
            maturity_date, days_to_maturity, last_price, bid, ask, spread_pct,
            volume, trades, financial_volume, underlying_price, moneyness_class,
            liquidity_score, risk_score, metadata_json
        ) VALUES (?, ?, ?, 'PETR4', 'CALL', 30, '2026-02-20', 40,
                  ?, 0.9, 1.1, 10, 10000, 100, 100000, 31, 'ATM', 80, 70, '{}')
        """,
        (trade_date, captured_at, ticker, price),
    )


def test_load_options_chain_snapshots_empty(tmp_path):
    assert load_options_chain_snapshots(tmp_path / "missing.db").empty
    assert get_available_option_history_range(tmp_path / "missing.db")["coverage_status"] == "SEM_DADOS"


def test_daily_chain_view_keeps_latest_snapshot(tmp_path):
    db = tmp_path / "db.sqlite"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        _insert_snapshot(con, "2026-01-02", "2026-01-02T10:00:00", price=1.0)
        _insert_snapshot(con, "2026-01-02", "2026-01-02T18:00:00", price=1.5)
        con.commit()

    df = load_options_chain_snapshots(db)
    daily = create_daily_chain_view(df)
    selected = get_chain_for_date(df, "2026-01-02", "PETR4")

    assert len(daily) == 1
    assert daily.loc[0, "last_price"] == 1.5
    assert selected.loc[0, "option_ticker"] == "PETRA300"
    assert get_available_option_history_range(db)["snapshots_count"] == 2

