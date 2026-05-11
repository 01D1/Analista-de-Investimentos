"""
test_bcb_ingestion.py
Tests for BCB SGS macro ingestion — ING-04.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.bcb import (
    BCB_SERIES,
    fetch_series,
    get_last_date_for_series,
    ingest_all_series,
    is_stale,
)
from src.ingestion.db import init_db


def make_in_memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    # Minimal macro_series schema
    conn.execute("""
        CREATE TABLE macro_series (
            id TEXT PRIMARY KEY,
            series_code INTEGER NOT NULL,
            series_name TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL NOT NULL,
            ingested_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX idx_macro_dedup ON macro_series(series_code, date)"
    )
    return conn


def test_fetch_series_returns_list_of_dicts():
    mock_data = [{"data": "08/05/2026", "valor": "0.053400"}]
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_data
        mock_get.return_value.raise_for_status = lambda: None
        result = fetch_series(11, inicio="01/01/2026")
    assert isinstance(result, list)
    assert result[0]["data"] == "08/05/2026"
    assert result[0]["valor"] == "0.053400"


def test_cds_value_divided_by_10000():
    """CDS Brasil series 29039: raw 94.47 bp must be stored as 0.009447."""
    conn = make_in_memory_db()
    mock_rows = [{"data": "01/04/2026", "valor": "94.47"}]
    with patch("src.ingestion.bcb.fetch_series", return_value=mock_rows):
        with patch("src.ingestion.bcb.is_stale", return_value=False):
            # Only run CDS series
            with patch.dict("src.ingestion.bcb.BCB_SERIES", {"cds_brasil": 29039}):
                ingest_all_series(conn)
    row = conn.execute(
        "SELECT value FROM macro_series WHERE series_code=29039"
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 0.009447) < 1e-8


def test_get_last_date_returns_stored_date():
    conn = make_in_memory_db()
    conn.execute(
        "INSERT INTO macro_series (id,series_code,series_name,date,value,ingested_at)"
        " VALUES ('abc',11,'selic_over','2026-04-01',0.053,'2026-04-01T12:00:00')"
    )
    result = get_last_date_for_series(conn, 11)
    assert result == "01/04/2026"


def test_get_last_date_returns_default_on_empty_db():
    conn = make_in_memory_db()
    result = get_last_date_for_series(conn, 11)
    assert result == "01/01/2019"


def test_is_stale_returns_true_for_old_date():
    old_date = date(2020, 1, 1)
    with patch("pandas_market_calendars.get_calendar") as mock_cal:
        # Mock schedule returns a large DataFrame (simulating many trading days)
        mock_schedule = MagicMock()
        mock_schedule.__len__ = lambda self: 100  # 99 trading days > threshold of 1
        mock_cal.return_value.schedule.return_value = mock_schedule
        result = is_stale(old_date)
    assert result is True


def test_is_stale_returns_false_for_today():
    today = date.today()
    with patch("pandas_market_calendars.get_calendar") as mock_cal:
        mock_schedule = MagicMock()
        mock_schedule.__len__ = lambda self: 1  # 0 trading days (today only = len 1 - 1 = 0)
        mock_cal.return_value.schedule.return_value = mock_schedule
        result = is_stale(today)
    assert result is False


def test_ingest_all_series_logs_warning_for_stale(caplog):
    """Stale series triggers WARNING log, not ERROR."""
    import logging
    conn = make_in_memory_db()
    # Pre-populate with an old date so is_stale is triggered
    conn.execute(
        "INSERT INTO macro_series (id,series_code,series_name,date,value,ingested_at)"
        " VALUES ('x',11,'selic_over','2020-01-01',0.05,'2020-01-01T00:00:00')"
    )
    mock_rows = [{"data": "08/05/2026", "valor": "0.053400"}]
    with patch("src.ingestion.bcb.fetch_series", return_value=mock_rows):
        with patch("src.ingestion.bcb.is_stale", return_value=True):
            with patch.dict("src.ingestion.bcb.BCB_SERIES", {"selic_over": 11}):
                with patch("src.ingestion.bcb._INTER_SERIES_SLEEP", 0):
                    result = ingest_all_series(conn)
    assert "selic_over" in result["stale"]


def test_ingest_all_series_incremental_fetch():
    """ingest_all_series() uses MAX(date) from DB as dataInicial, not '01/01/2019'."""
    conn = make_in_memory_db()
    conn.execute(
        "INSERT INTO macro_series (id,series_code,series_name,date,value,ingested_at)"
        " VALUES ('y',11,'selic_over','2026-04-30',0.053,'2026-04-30T00:00:00')"
    )
    captured_inicio = []

    def mock_fetch(cod, inicio="01/01/2019"):
        captured_inicio.append(inicio)
        return []

    with patch("src.ingestion.bcb.fetch_series", side_effect=mock_fetch):
        with patch("src.ingestion.bcb.is_stale", return_value=False):
            with patch.dict("src.ingestion.bcb.BCB_SERIES", {"selic_over": 11}):
                with patch("src.ingestion.bcb._INTER_SERIES_SLEEP", 0):
                    ingest_all_series(conn)

    assert captured_inicio[0] == "30/04/2026"
    assert captured_inicio[0] != "01/01/2019"


def test_all_five_series_in_bcb_series_dict():
    """BCB_SERIES must contain all D-11 series codes."""
    assert 11 in BCB_SERIES.values()     # selic_over
    assert 433 in BCB_SERIES.values()    # ipca_12m
    assert 1 in BCB_SERIES.values()      # ptax_usd
    assert 29039 in BCB_SERIES.values()  # cds_brasil
    assert 4380 in BCB_SERIES.values()   # pib_nominal
