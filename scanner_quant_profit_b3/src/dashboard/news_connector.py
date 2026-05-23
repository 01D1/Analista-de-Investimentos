"""News Hunter connector — reads from 12_PYTHON/news_hunter/banco.db.

Provides a clean interface for app pages to consume News Hunter data
without creating mocks. All data is real, sourced from the external vault.

Usage:
    from src.dashboard.news_connector import get_recent_news, get_news_for_ticker

    news = get_recent_news(limit=20)           # all recent news
    news = get_recent_news(ticker="PETR4", limit=10)  # filtered by ticker
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

# Path to News Hunter banco.db — external OBSIDIAN vault (OneDrive)
# Resolves by walking up from app root to find the vault, then 12_PYTHON/news_hunter
def _resolve_news_hunter_path() -> Path:
    app_root = Path(__file__).resolve().parents[2]
    # Walk up to find vault that contains 12_PYTHON
    p = app_root.parent
    while p.name and p != p.parent:
        candidate = p / "12_PYTHON" / "news_hunter" / "banco.db"
        if candidate.exists():
            return candidate
        p = p.parent
    # Fallback: direct OneDrive path
    return Path.home() / "Library/CloudStorage/OneDrive-EPEJUD/DIEGO/OBSIDIAN/Analista de Investimentos/12_PYTHON/news_hunter/banco.db"


_NEWS_HUNTER_PATH = _resolve_news_hunter_path()

# Fallback to local news if external path unavailable
_LOCAL_DB = Path(__file__).resolve().parents[2] / "data" / "database" / "scanner_quant.db"


def _news_db_path() -> Path:
    """Resolve the news database path. Prefers external vault, falls back to local."""
    if _NEWS_HUNTER_PATH.exists():
        return _NEWS_HUNTER_PATH
    return _LOCAL_DB


def get_recent_news(ticker: str | None = None, limit: int = 20) -> list[dict]:
    """Get recent news, optionally filtered by ticker.

    Args:
        ticker: Optional ticker filter (e.g. "PETR4"). Matches against tickers field.
        limit: Maximum number of news items to return.

    Returns:
        List of news dicts with: id, titulo, fonte, categoria, data_coleta,
        data_pub, resumo_ia, sentimento, impacto_macro, tickers, urgente, score.
    """
    db_path = _news_db_path()
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        if ticker:
            # Match tickers containing the given ticker (comma-separated field)
            query = """
                SELECT id, titulo, fonte, categoria, data_coleta, data_pub,
                       resumo_ia, sentimento, impacto_macro, tickers, urgente, score,
                       data_coleta as ts
                FROM noticias
                WHERE tickers LIKE ?
                   OR tickers LIKE ?
                   OR tickers LIKE ?
                ORDER BY data_coleta DESC, data_pub DESC
                LIMIT ?
            """
            like_pattern = f"%{ticker}%"
            like_start = f"{ticker},%"
            like_end = f"%,{ticker}%"
            rows = conn.execute(query, (like_pattern, like_start, like_end, limit)).fetchall()
        else:
            query = """
                SELECT id, titulo, fonte, categoria, data_coleta, data_pub,
                       resumo_ia, sentimento, impacto_macro, tickers, urgente, score,
                       data_coleta as ts
                FROM noticias
                ORDER BY data_coleta DESC, data_pub DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()

        conn.close()

        news = []
        for row in rows:
            # Parse data fields
            data_coleta = row["data_coleta"] or ""
            data_pub = row["data_pub"] or ""
            ts = row["ts"] or ""

            # Build parsed dict
            news.append({
                "id": row["id"],
                "titulo": row["titulo"] or "",
                "fonte": row["fonte"] or "",
                "categoria": row["categoria"] or "",
                "data_coleta": data_coleta,
                "data_pub": data_pub,
                "ts": ts,  # alias for data_coleta
                "resumo_ia": row["resumo_ia"] or "",
                "sentimento": row["sentimento"] or "",
                "impacto_macro": row["impacto_macro"] or "",
                "tickers": row["tickers"] or "",
                "urgente": bool(row["urgente"]),
                "score": row["score"],
            })

        return news

    except sqlite3.OperationalError:
        return []
    except Exception:
        return []


def get_news_summary(ticker: str | None = None, limit: int = 10) -> dict:
    """Get news summary with counts by category/sentiment.

    Args:
        ticker: Optional ticker filter.
        limit: Max items for the recent news list.

    Returns:
        Dict with: total, urgent_count, positive_count, negative_count,
        neutral_count, recent (list of news dicts).
    """
    news = get_recent_news(ticker=ticker, limit=limit * 10)  # fetch more for stats

    if not news:
        return {
            "total": 0,
            "urgent_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "recent": [],
        }

    urgent_count = sum(1 for n in news if n["urgente"])
    positive_count = sum(
        1 for n in news
        if n["sentimento"] and n["sentimento"].lower() in ("positivo", "alta", "high", "bull")
    )
    negative_count = sum(
        1 for n in news
        if n["sentimento"] and n["sentimento"].lower() in ("negativo", "queda", "low", "bear")
    )
    neutral_count = sum(
        1 for n in news
        if n["sentimento"] and n["sentimento"].lower() in ("neutro", "neutral", "mixed")
    )

    return {
        "total": len(news),
        "urgent_count": urgent_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "recent": news[:limit],
    }


def get_news_for_page(ticker: str | None = None, max_items: int = 5) -> list[dict]:
    """Get news for dashboard page consumption — concise version.

    Returns a lightweight news list suitable for display in pages.
    """
    return get_recent_news(ticker=ticker, limit=max_items)