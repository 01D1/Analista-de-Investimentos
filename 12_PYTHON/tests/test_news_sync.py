"""
test_news_sync.py
Tests for news sync from banco.db to ingestion.db — ING-06.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.ingestion.news_sync import sync_news_to_ingestion_db, _is_b3_ticker
from src.ingestion.db import init_db


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_banco_db(tmp_path: Path, rows: list[dict]) -> Path:
    """Create a minimal banco.db with noticias rows for testing."""
    db_path = tmp_path / "banco.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE noticias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE NOT NULL,
            titulo TEXT,
            link TEXT,
            fonte TEXT,
            categoria TEXT,
            data_coleta TEXT,
            data_pub TEXT,
            score INTEGER DEFAULT 0
        )
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO noticias (hash, titulo, link, fonte, categoria, data_coleta, data_pub, score)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.get("hash", f"hash_{r['link']}"),
                r.get("titulo", "Título Teste"),
                r["link"],
                r.get("fonte", "Fonte Teste"),
                r.get("categoria", ""),
                "2026-05-10T12:00:00",
                r.get("data_pub", "2026-05-10"),
                r.get("score", 0),
            ),
        )
    conn.commit()
    conn.close()
    return db_path


def make_ingestion_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "ingestion.db"
    init_db(db_path)
    return sqlite3.connect(db_path)


# ─── Tests ──────────────────────────────────────────────────────────────────

def test_sync_copies_articles(tmp_path):
    """sync_news_to_ingestion_db() inserts all source rows on first call."""
    rows = [
        {"link": "https://example.com/a", "titulo": "Notícia A"},
        {"link": "https://example.com/b", "titulo": "Notícia B"},
        {"link": "https://example.com/c", "titulo": "Notícia C"},
    ]
    banco = make_banco_db(tmp_path, rows)
    conn = make_ingestion_db(tmp_path)

    inserted = sync_news_to_ingestion_db(conn, banco_db_path=banco)
    assert inserted == 3

    count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
    assert count == 3
    conn.close()


def test_sync_deduplicates_by_url(tmp_path):
    """Second sync call inserts 0 rows when all URLs already present."""
    rows = [{"link": "https://example.com/a", "titulo": "Notícia A"}]
    banco = make_banco_db(tmp_path, rows)
    conn = make_ingestion_db(tmp_path)

    sync_news_to_ingestion_db(conn, banco_db_path=banco)
    second = sync_news_to_ingestion_db(conn, banco_db_path=banco)

    assert second == 0
    count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
    assert count == 1
    conn.close()


def test_b3_ticker_stored_in_ticker_tags(tmp_path):
    """categoria='PETR4' → ticker_tags='[\"PETR4\"]' in news_articles."""
    rows = [{"link": "https://example.com/petr4", "titulo": "PETR4 sobe", "categoria": "PETR4"}]
    banco = make_banco_db(tmp_path, rows)
    conn = make_ingestion_db(tmp_path)

    sync_news_to_ingestion_db(conn, banco_db_path=banco)

    row = conn.execute("SELECT ticker_tags FROM news_articles WHERE url LIKE '%petr4%'").fetchone()
    assert row is not None
    tags = json.loads(row[0])
    assert tags == ["PETR4"]
    conn.close()


def test_non_ticker_categoria_gives_null_ticker_tags(tmp_path):
    """categoria='economia' → ticker_tags IS NULL."""
    rows = [{"link": "https://example.com/eco", "titulo": "Economia", "categoria": "economia"}]
    banco = make_banco_db(tmp_path, rows)
    conn = make_ingestion_db(tmp_path)

    sync_news_to_ingestion_db(conn, banco_db_path=banco)

    row = conn.execute("SELECT ticker_tags FROM news_articles").fetchone()
    assert row[0] is None
    conn.close()


def test_sync_returns_zero_when_banco_db_missing(tmp_path):
    """sync_news_to_ingestion_db() returns 0 when banco.db does not exist."""
    conn = make_ingestion_db(tmp_path)
    missing_path = tmp_path / "nonexistent.db"

    result = sync_news_to_ingestion_db(conn, banco_db_path=missing_path)

    assert result == 0
    count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
    assert count == 0
    conn.close()


def test_sync_respects_limit(tmp_path):
    """limit parameter controls max rows read from banco.db."""
    rows = [{"link": f"https://example.com/{i}", "titulo": f"Título {i}"} for i in range(10)]
    banco = make_banco_db(tmp_path, rows)
    conn = make_ingestion_db(tmp_path)

    inserted = sync_news_to_ingestion_db(conn, limit=3, banco_db_path=banco)
    assert inserted == 3
    conn.close()


def test_banco_db_not_modified(tmp_path):
    """banco.db noticias count unchanged after sync (read-only access)."""
    rows = [{"link": "https://example.com/x", "titulo": "X"}]
    banco = make_banco_db(tmp_path, rows)
    conn = make_ingestion_db(tmp_path)

    before = sqlite3.connect(banco).execute("SELECT COUNT(*) FROM noticias").fetchone()[0]
    sync_news_to_ingestion_db(conn, banco_db_path=banco)
    after = sqlite3.connect(banco).execute("SELECT COUNT(*) FROM noticias").fetchone()[0]

    assert before == after == 1
    conn.close()


# ─── Unit tests for _is_b3_ticker ───────────────────────────────────────────

def test_is_b3_ticker_valid():
    assert _is_b3_ticker("PETR4") is True
    assert _is_b3_ticker("VALE3") is True
    assert _is_b3_ticker("SANB11") is True


def test_is_b3_ticker_invalid():
    assert _is_b3_ticker("economia") is False
    assert _is_b3_ticker("PETR") is False       # no digit
    assert _is_b3_ticker("PETROLEO") is False
    assert _is_b3_ticker("") is False
