"""
test_b3_ingestion.py
Tests for B3 OHLCV ingestion — ING-05.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.ingestion.b3_scraper import B3Scraper
from src.ingestion.db import init_db


def make_price_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE price_ohlcv (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL,
            close REAL, adj_close REAL, volume INTEGER,
            is_gap INTEGER DEFAULT 0,
            ingested_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX idx_price_dedup ON price_ohlcv(ticker, date);
    """)
    return conn


def make_ohlcv_df(dates: list[str]) -> pd.DataFrame:
    """Build minimal OHLCV DataFrame with given ISO date strings."""
    idx = pd.to_datetime(dates)
    return pd.DataFrame(
        {
            "open":   [10.0] * len(dates),
            "high":   [11.0] * len(dates),
            "low":    [9.0] * len(dates),
            "close":  [10.5] * len(dates),
            "volume": [1000] * len(dates),
        },
        index=idx,
    )


def test_write_to_db_inserts_rows():
    conn = make_price_db()
    scraper = B3Scraper()
    df = make_ohlcv_df(["2026-05-05", "2026-05-06", "2026-05-07"])
    inserted = scraper.write_to_db("PETR4", df, conn)
    assert inserted == 3
    count = conn.execute(
        "SELECT COUNT(*) FROM price_ohlcv WHERE ticker='PETR4' AND is_gap=0"
    ).fetchone()[0]
    assert count == 3


def test_write_to_db_deduplicates():
    conn = make_price_db()
    scraper = B3Scraper()
    df = make_ohlcv_df(["2026-05-05"])
    scraper.write_to_db("PETR4", df, conn)
    second = scraper.write_to_db("PETR4", df, conn)
    assert second == 0


def test_detect_and_insert_gaps_flags_missing_days():
    conn = make_price_db()
    scraper = B3Scraper()

    # Provide df with only 3 days
    df = make_ohlcv_df(["2026-05-04", "2026-05-05", "2026-05-07"])

    # Mock calendar to return 5 expected trading days
    expected_trading_dates = [
        date(2026, 5, 4),
        date(2026, 5, 5),
        date(2026, 5, 6),   # missing in df
        date(2026, 5, 7),
        date(2026, 5, 8),   # missing in df
    ]
    mock_schedule = MagicMock()
    mock_schedule.index = pd.DatetimeIndex([
        pd.Timestamp(d) for d in expected_trading_dates
    ])

    with patch("pandas_market_calendars.get_calendar") as mock_cal:
        mock_cal.return_value.schedule.return_value = mock_schedule
        gaps = scraper.detect_and_insert_gaps("VALE3", df, "2026-05-04", conn)

    assert gaps == 2
    gap_rows = conn.execute(
        "SELECT date FROM price_ohlcv WHERE ticker='VALE3' AND is_gap=1"
    ).fetchall()
    gap_dates = {r[0] for r in gap_rows}
    assert "2026-05-06" in gap_dates
    assert "2026-05-08" in gap_dates


def test_no_gap_interpolation():
    """Gap rows must have NULL close/open/high/low — never estimated prices."""
    conn = make_price_db()
    scraper = B3Scraper()
    df = make_ohlcv_df(["2026-05-05"])

    mock_schedule = MagicMock()
    mock_schedule.index = pd.DatetimeIndex([
        pd.Timestamp("2026-05-05"),
        pd.Timestamp("2026-05-06"),  # gap
    ])

    with patch("pandas_market_calendars.get_calendar") as mock_cal:
        mock_cal.return_value.schedule.return_value = mock_schedule
        scraper.detect_and_insert_gaps("PETR4", df, "2026-05-05", conn)

    gap_row = conn.execute(
        "SELECT open, close FROM price_ohlcv WHERE ticker='PETR4' AND is_gap=1"
    ).fetchone()
    assert gap_row is not None
    assert gap_row[0] is None  # open is NULL for gap rows
    assert gap_row[1] is None  # close is NULL for gap rows


def test_multiindex_columns_normalized():
    """B3Scraper._download() flattens MultiIndex columns to lowercase strings."""
    import yfinance as yf
    scraper = B3Scraper()

    # Build MultiIndex DataFrame similar to yfinance 1.3.x output
    arrays = [["Close", "Open"], ["PETR4.SA", "PETR4.SA"]]
    multi_idx = pd.MultiIndex.from_arrays(arrays)
    raw = pd.DataFrame(
        [[10.5, 9.0]],
        index=pd.DatetimeIndex(["2026-05-07"]),
        columns=multi_idx,
    )

    with patch("yfinance.download", return_value=raw):
        result = scraper._download("PETR4", "2026-05-07")

    assert not isinstance(result.columns, pd.MultiIndex)
    assert "close" in result.columns or "open" in result.columns


def test_fetch_and_store_incremental():
    """fetch_and_store() uses MAX(date) from DB, not DEFAULT_START, for existing ticker."""
    conn = make_price_db()
    # Pre-populate with a row so MAX(date) = 2026-04-30
    conn.execute(
        """INSERT INTO price_ohlcv
           (id,ticker,date,open,high,low,close,adj_close,volume,is_gap,ingested_at)
           VALUES ('x','PETR4','2026-04-30',10,11,9,10.5,10.5,1000,0,'2026-04-30T00:00:00')"""
    )
    conn.commit()

    captured_since = []

    def mock_fetch(ticker, start_date=None, force=False):
        captured_since.append(start_date)
        return pd.DataFrame()  # empty — just testing the since value

    scraper = B3Scraper()
    with patch.object(scraper, "fetch", side_effect=mock_fetch):
        with patch.object(scraper, "detect_and_insert_gaps", return_value=0):
            scraper.fetch_and_store("PETR4", conn)

    assert captured_since[0] == "2026-05-01"  # day after 2026-04-30
    assert captured_since[0] != "2019-01-01"  # not the default start
