"""
test_financial_signals.py
Tests for FIN-06 technical signal computation in src/financial_engine.py.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helper: synthetic price series
# ---------------------------------------------------------------------------

def make_price_series(n: int = 250, start: float = 100.0, trend: float = 0.001) -> pd.Series:
    """Build synthetic ascending price series for signal tests.

    Args:
        n:     Number of data points (business days).
        start: Starting price.
        trend: Mean daily return (0.001 = +0.1%/day).

    Returns:
        pd.Series with ISO date strings as index and float prices as values.
    """
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    prices = start * np.cumprod(1 + trend + rng.normal(0, 0.01, n))
    return pd.Series(prices.tolist(), index=[str(d.date()) for d in idx])


# ---------------------------------------------------------------------------
# In-memory DB helper for gap-exclusion test
# ---------------------------------------------------------------------------

_SIGNALS_SCHEMA = """
CREATE TABLE price_ohlcv (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    adj_close REAL, volume INTEGER,
    is_gap INTEGER DEFAULT 0,
    ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_price_dedup ON price_ohlcv(ticker, date);

CREATE TABLE financial_signals (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    computed_date TEXT NOT NULL,
    rsi_14 REAL, macd_line REAL, macd_signal REAL, macd_histogram REAL,
    ma_50 REAL, ma_200 REAL, golden_cross INTEGER, death_cross INTEGER,
    momentum_score INTEGER, ingested_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_signals_dedup ON financial_signals(ticker, computed_date);
"""


def make_signals_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with price_ohlcv and financial_signals tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SIGNALS_SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Test 1: RSI-14 range
# ---------------------------------------------------------------------------

def test_rsi_14_computation():
    """RSI-14 must always return a float in [0, 100]."""
    from src.financial_engine import compute_signals

    prices = make_price_series(250)
    result = compute_signals(prices)

    assert isinstance(result["rsi_14"], float), (
        f"Expected rsi_14 to be float, got {type(result['rsi_14'])}"
    )
    assert 0 <= result["rsi_14"] <= 100, (
        f"RSI-14 out of range [0, 100]: {result['rsi_14']}"
    )


# ---------------------------------------------------------------------------
# Test 2: MACD 12/26/9 components
# ---------------------------------------------------------------------------

def test_macd_12_26_9():
    """MACD histogram must equal macd_line - macd_signal (within floating-point tolerance)."""
    from src.financial_engine import compute_signals

    prices = make_price_series(250)
    result = compute_signals(prices)

    assert "macd_line" in result, "macd_line missing from compute_signals result"
    assert "macd_signal" in result, "macd_signal missing from compute_signals result"
    assert "macd_histogram" in result, "macd_histogram missing from compute_signals result"

    # Histogram = line - signal (identity relationship)
    diff = abs(result["macd_line"] - result["macd_signal"] - result["macd_histogram"])
    assert diff < 0.001, (
        f"MACD identity violated: |line({result['macd_line']}) - "
        f"signal({result['macd_signal']}) - hist({result['macd_histogram']})| = {diff}"
    )


# ---------------------------------------------------------------------------
# Test 3: MA crossover detection
# ---------------------------------------------------------------------------

def test_ma_crossover_detection():
    """MA50 and MA200 are positive; golden/death cross are mutually exclusive."""
    from src.financial_engine import compute_signals

    prices = make_price_series(250, trend=0.002)  # strong uptrend
    result = compute_signals(prices)

    assert "ma_50" in result, "ma_50 missing from result"
    assert "ma_200" in result, "ma_200 missing from result"
    assert result["ma_50"] is not None and result["ma_50"] > 0, (
        f"ma_50 should be positive, got {result['ma_50']}"
    )
    assert result["ma_200"] is not None and result["ma_200"] > 0, (
        f"ma_200 should be positive, got {result['ma_200']}"
    )
    assert result["golden_cross"] in (0, 1), (
        f"golden_cross must be 0 or 1, got {result['golden_cross']}"
    )
    assert result["death_cross"] in (0, 1), (
        f"death_cross must be 0 or 1, got {result['death_cross']}"
    )
    # Golden cross and death cross are mutually exclusive
    assert not (result["golden_cross"] == 1 and result["death_cross"] == 1), (
        "golden_cross and death_cross cannot both be 1 (mutually exclusive)"
    )


# ---------------------------------------------------------------------------
# Test 4: Momentum score range and multiples of 10
# ---------------------------------------------------------------------------

def test_momentum_score_range():
    """Composite momentum score must be in [0, 100] and a multiple of 10."""
    from src.financial_engine import compute_signals

    prices = make_price_series(250)
    result = compute_signals(prices)

    assert 0 <= result["momentum_score"] <= 100, (
        f"momentum_score out of [0, 100]: {result['momentum_score']}"
    )
    assert result["momentum_score"] % 10 == 0, (
        f"momentum_score must be a multiple of 10, got {result['momentum_score']}"
    )


# ---------------------------------------------------------------------------
# Test 5: Gap rows (is_gap=1) excluded from signal computation
# ---------------------------------------------------------------------------

def test_gap_rows_excluded():
    """_compute_and_write_signals() excludes is_gap=1 rows; computation uses only clean prices."""
    from src.financial_engine import _compute_and_write_signals

    conn = make_signals_db()
    now = "2026-05-11T00:00:00"

    # Insert 250 clean rows (is_gap=0) with valid adj_close
    import pandas as pd
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    rng = np.random.default_rng(99)
    prices_arr = 100.0 * np.cumprod(1 + 0.001 + rng.normal(0, 0.01, 250))

    for i, (d, p) in enumerate(zip(dates, prices_arr)):
        date_str = str(d.date())
        conn.execute(
            """INSERT OR IGNORE INTO price_ohlcv
               (id, ticker, date, open, high, low, close, adj_close, volume, is_gap, ingested_at)
               VALUES (?, 'TEST', ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (str(uuid.uuid4()), date_str, p, p + 0.5, p - 0.5, p + 0.1, p, 1000, now),
        )
    conn.commit()

    # Insert 10 additional rows with is_gap=1 and adj_close=NULL
    # These should be completely ignored by the signals query
    gap_dates = pd.date_range("2025-06-01", periods=10, freq="B")
    for d in gap_dates:
        date_str = str(d.date())
        conn.execute(
            """INSERT OR IGNORE INTO price_ohlcv
               (id, ticker, date, open, high, low, close, adj_close, volume, is_gap, ingested_at)
               VALUES (?, 'TEST', ?, NULL, NULL, NULL, NULL, NULL, NULL, 1, ?)""",
            (str(uuid.uuid4()), date_str, now),
        )
    conn.commit()

    # Call _compute_and_write_signals — gap rows must be excluded (is_gap=0 filter)
    _compute_and_write_signals("TEST", conn, "2026-05-11")

    # Assert exactly 1 row written to financial_signals
    rows = conn.execute(
        "SELECT * FROM financial_signals WHERE ticker = 'TEST'"
    ).fetchall()
    assert len(rows) == 1, f"Expected 1 row in financial_signals, got {len(rows)}"

    # Assert rsi_14 is not None (gap rows excluded — computation succeeded with 250 clean rows)
    row = rows[0]
    assert row["rsi_14"] is not None, (
        "rsi_14 should not be None — 250 clean rows should produce valid RSI"
    )

    # Assert momentum_score is not None (full computation succeeded)
    assert row["momentum_score"] is not None, (
        "momentum_score should not be None — gap rows must not have polluted computation"
    )
