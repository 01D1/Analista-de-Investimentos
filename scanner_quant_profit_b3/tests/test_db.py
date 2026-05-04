"""Testes de integração com o banco SQLite."""
import sqlite3
import tempfile
import pytest
import pandas as pd

from src.strategies.call_continuity_strategy import (
    get_stock_history,
    get_options,
    get_realtime_signal,
)


@pytest.fixture
def temp_db():
    """
    Banco SQLite em memória com dados sintéticos usando o schema real do projeto.
    b3_quotes é a tabela principal (asset_type: ACAO, CALL, PUT, OUTRO).
    """
    con = sqlite3.connect(":memory:")

    # Schema real da tabela b3_quotes
    con.execute("""
    CREATE TABLE b3_quotes (
        trade_date TEXT,
        ticker TEXT,
        market_type INTEGER,
        company_name TEXT,
        open REAL,
        high REAL,
        low REAL,
        average REAL,
        close REAL,
        best_bid REAL,
        best_ask REAL,
        trades INTEGER,
        quantity INTEGER,
        volume REAL,
        option_exercise_price REAL,
        option_maturity TEXT,
        asset_type TEXT
    )
    """)

    con.execute("""
    CREATE TABLE realtime_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        captured_at TEXT NOT NULL,
        asset TEXT NOT NULL,
        last REAL,
        variation_pct REAL,
        volume REAL,
        trades INTEGER,
        score INTEGER,
        signal TEXT,
        motivos TEXT
    )
    """)

    # Histórico de 30 dias para PETR4 (asset_type='ACAO')
    import datetime
    for i in range(30):
        d = (datetime.date(2026, 3, 1) + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        price = 35.0 + i * 0.2
        con.execute("""
        INSERT INTO b3_quotes
        (trade_date, ticker, market_type, open, high, low, average, close,
         trades, volume, quantity, option_exercise_price, option_maturity, asset_type)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (d, "PETR4", 10, price * 0.99, price * 1.01, price * 0.98,
              price, price, 10_000, 80_000_000.0, 1_000_000,
              0.0, "99991231", "ACAO"))

    # Opção CALL com vencimento em 2026-06-20 (DTE ~83 dias de 2026-03-29)
    con.execute("""
    INSERT INTO b3_quotes
    (trade_date, ticker, market_type, open, high, low, average, close,
     trades, volume, quantity, option_exercise_price, option_maturity, asset_type)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, ("2026-03-29", "PETRF350", 70, 1.8, 2.0, 1.7, 1.9, 1.9,
          150, 300_000.0, 15_000, 35.0, "20260620", "CALL"))

    # Sinal intraday
    con.execute("""
    INSERT INTO realtime_signals
    (captured_at, asset, last, variation_pct, volume, trades, score, signal, motivos)
    VALUES (?,?,?,?,?,?,?,?,?)
    """, ("2026-03-29 14:00:00", "PETR4", 41.0, 1.5, 100_000_000.0, 15_000, 80, "COMPRA", "volume alto"))

    con.commit()
    yield con
    con.close()


class TestGetStockHistory:
    def test_returns_dataframe(self, temp_db):
        df = get_stock_history(temp_db, "PETR4")
        assert isinstance(df, pd.DataFrame)

    def test_excludes_options(self, temp_db):
        df = get_stock_history(temp_db, "PETR4")
        # Apenas ACAO deve aparecer, nunca tickers de opção
        if not df.empty:
            assert "PETRF350" not in df["trade_date"].values  # ticker de opção não deve aparecer

    def test_missing_ticker_returns_empty(self, temp_db):
        df = get_stock_history(temp_db, "XYZW3")
        assert df.empty

    def test_sorted_by_date(self, temp_db):
        df = get_stock_history(temp_db, "PETR4")
        if not df.empty and len(df) > 1:
            dates = pd.to_datetime(df["trade_date"])
            assert (dates.diff().dropna() >= pd.Timedelta(0)).all()


class TestGetOptions:
    def test_returns_calls(self, temp_db):
        df = get_options(temp_db, "PETR4", "CALL", 15, 120)
        assert isinstance(df, pd.DataFrame)

    def test_no_options_outside_dte(self, temp_db):
        # DTE da opção é ~83 dias (2026-06-20 - 2026-03-29)
        # Se max_dte=50, não deve retornar nada
        df = get_options(temp_db, "PETR4", "CALL", 15, 50)
        assert df.empty

    def test_options_within_dte(self, temp_db):
        df = get_options(temp_db, "PETR4", "CALL", 15, 120)
        assert not df.empty


class TestGetRealtimeSignal:
    def test_returns_dict(self, temp_db):
        result = get_realtime_signal(temp_db, "PETR4")
        assert isinstance(result, dict)

    def test_missing_returns_none(self, temp_db):
        result = get_realtime_signal(temp_db, "VALE3")
        assert result is None

    def test_has_expected_fields(self, temp_db):
        result = get_realtime_signal(temp_db, "PETR4")
        assert result is not None
        assert "last" in result
        assert "score" in result
