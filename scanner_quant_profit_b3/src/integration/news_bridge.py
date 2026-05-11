"""
News Bridge — lê diretamente o banco.db do news_hunter.

Fonte primária: 12_PYTHON/news_hunter/banco.db (tabela noticias)
Fallback:       arquivos JSON/CSV em outputs_dir (comportamento anterior)

Somente leitura — nunca altera o news_hunter.
"""
from __future__ import annotations

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger("radar_quant.news_bridge")

# ── Localização do news_hunter ────────────────────────────────────────────────

_THIS    = Path(__file__).resolve()
_VAULT   = _THIS.parents[4]
_NH_DIR  = _VAULT / "12_PYTHON" / "news_hunter"
_NH_DB   = _NH_DIR / "banco.db"


def nh_db_available() -> bool:
    return _NH_DB.exists()


# ── Busca no banco.db ─────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_NH_DB)
    con.row_factory = sqlite3.Row
    return con


def get_news_for_asset(
    ticker: str,
    days: int = 7,
    limit: int = 5,
) -> list[dict]:
    """
    Busca notícias relevantes para um ativo no banco do news_hunter.

    Busca por `ticker` e pelo nome empresa (ex: PETR4 → 'petrobras') no
    título e conteúdo da notícia. Retorna lista ordenada por score desc.
    """
    if not nh_db_available():
        return []

    # mapeamento ticker → palavras-chave de busca
    _KEYWORD_MAP = {
        "PETR4": ["petrobras", "petr4", "petr3"],
        "PETR3": ["petrobras", "petr3", "petr4"],
        "VALE3": ["vale", "vale3", "minério de ferro"],
        "ITUB4": ["itaú", "itub4", "itub3"],
        "ITUB3": ["itaú", "itub3", "itub4"],
        "BBDC4": ["bradesco", "bbdc4", "bbdc3"],
        "BBDC3": ["bradesco", "bbdc3", "bbdc4"],
        "BBAS3": ["banco do brasil", "bbas3"],
        "WEGE3": ["weg", "wege3"],
        "ABEV3": ["ambev", "abev3"],
        "MGLU3": ["magazine luiza", "magalu", "mglu3"],
        "RENT3": ["localiza", "rent3"],
        "ELET3": ["eletrobras", "elet3", "elet6"],
        "ELET6": ["eletrobras", "elet6", "elet3"],
        "RAIZ4": ["raízen", "raiz4"],
        "BPAC11":["btg", "bpac11"],
        "CPLE6": ["copel", "cple6"],
        "SUZB3": ["suzano", "suzb3"],
        "GGBR4": ["gerdau", "ggbr4"],
        "CSNA3": ["csn", "csna3"],
        "BEEF3": ["minerva", "beef3"],
        "MRVE3": ["mrv", "mrve3"],
    }

    keywords = _KEYWORD_MAP.get(ticker.upper(), [ticker.lower()])
    since    = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    like_clauses = " OR ".join(
        ["(LOWER(titulo) LIKE ? OR LOWER(conteudo) LIKE ?)"] * len(keywords)
    )
    params = []
    for kw in keywords:
        params += [f"%{kw}%", f"%{kw}%"]
    params.append(since)

    sql = f"""
        SELECT titulo, fonte, categoria, data_pub, data_coleta, link, score, resumo_curto
        FROM noticias
        WHERE ({like_clauses})
          AND data_coleta >= ?
        ORDER BY score DESC, data_coleta DESC
        LIMIT {limit}
    """

    try:
        with _conn() as con:
            rows = con.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("news_bridge query error: %s", e)
        return []


def get_news_batch(
    tickers: list[str],
    outputs_dir: str | Path = "",
    days: int = 7,
    limit_per_asset: int = 3,
) -> dict[str, dict]:
    """
    Retorna {ticker: {"headline", "headline_date", "headline_source"}}
    para uma lista de tickers. Compatível com a assinatura anterior.
    """
    result: dict[str, dict] = {}

    if nh_db_available():
        for ticker in tickers:
            news = get_news_for_asset(ticker, days=days, limit=1)
            if news:
                n = news[0]
                result[ticker] = {
                    "headline":        str(n.get("titulo", "")),
                    "headline_date":   str(n.get("data_pub") or n.get("data_coleta", "")),
                    "headline_source": str(n.get("fonte", "")),
                }
            else:
                result[ticker] = {}
        return result

    # Fallback: arquivos JSON/CSV (comportamento original)
    if outputs_dir:
        return _batch_from_files(tickers, Path(outputs_dir))

    return {t: {} for t in tickers}


def get_news(ticker: str, outputs_dir: str | Path = "") -> dict:
    """Retorna manchete mais recente. Compatível com assinatura original."""
    batch = get_news_batch([ticker], outputs_dir=outputs_dir)
    return batch.get(ticker, {})


def get_recent_alerts(limit: int = 20, days: int = 3) -> pd.DataFrame:
    """Retorna DataFrame das notícias urgentes/alerta recentes."""
    if not nh_db_available():
        return pd.DataFrame()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql   = """
        SELECT titulo, fonte, categoria, data_pub, score, link
        FROM noticias
        WHERE (urgente = 1 OR score >= 8)
          AND data_coleta >= ?
        ORDER BY score DESC, data_coleta DESC
        LIMIT ?
    """
    try:
        with _conn() as con:
            return pd.read_sql(sql, con, params=(since, limit))
    except Exception:
        return pd.DataFrame()


def get_all_recent(days: int = 2, limit: int = 50) -> pd.DataFrame:
    """Últimas notícias do banco, para o painel geral."""
    if not nh_db_available():
        return pd.DataFrame()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql   = """
        SELECT titulo, fonte, categoria, data_pub, score, link, resumo_curto
        FROM noticias
        WHERE data_coleta >= ?
        ORDER BY score DESC, data_coleta DESC
        LIMIT ?
    """
    try:
        with _conn() as con:
            return pd.read_sql(sql, con, params=(since, limit))
    except Exception:
        return pd.DataFrame()


# ── Fallback: arquivos (mantém compatibilidade) ───────────────────────────────

def _load_combined(outputs_dir: Path) -> dict:
    p = outputs_dir / "news_latest.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _batch_from_files(tickers: list[str], outputs_dir: Path) -> dict[str, dict]:
    combined = _load_combined(outputs_dir)
    result   = {}
    for t in tickers:
        if t in combined:
            e = combined[t]
            result[t] = {
                "headline":        str(e.get("headline", e.get("title", ""))),
                "headline_date":   str(e.get("date", "")),
                "headline_source": str(e.get("source", "")),
            }
        else:
            result[t] = {}
    return result
