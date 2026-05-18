"""Auditoria de News Hunter e pipeline de eventos."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.data_quality.source_inventory import make_audit_row, resolve_path, table_exists
from src.utils import load_config, project_path


def _columns(con, table: str) -> list[str]:
    try:
        return [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def audit_news_hunter(db_path: str | Path = "../12_PYTHON/news_hunter/banco.db") -> dict:
    path = resolve_path(db_path) or Path(db_path)
    if not path.exists():
        return make_audit_row(
            source_name="news_hunter",
            source_type="NEWS",
            primary_or_secondary="SECONDARY",
            expected_path_or_url=str(path),
            status="MISSING",
            message="Banco News Hunter nao encontrado.",
        )
    try:
        with sqlite3.connect(path) as con:
            if not table_exists(con, "noticias"):
                return make_audit_row(
                    source_name="news_hunter",
                    source_type="NEWS",
                    primary_or_secondary="SECONDARY",
                    expected_path_or_url=str(path),
                    available=True,
                    status="ERROR",
                    message="Tabela noticias nao encontrada.",
                )
            cols = _columns(con, "noticias")
            count = int(con.execute("SELECT COUNT(*) FROM noticias").fetchone()[0] or 0)
            date_col = next((c for c in ["data", "date", "published_at", "created_at"] if c in cols), None)
            title_col = next((c for c in ["titulo", "title", "headline"] if c in cols), None)
            source_col = next((c for c in ["fonte", "source", "source_name"] if c in cols), None)
            ticker_col = next((c for c in ["ticker", "tickers", "ativo"] if c in cols), None)
            latest = con.execute(f"SELECT MAX({date_col}) FROM noticias").fetchone()[0] if date_col else ""
            missing_dates = int(con.execute(f"SELECT COUNT(*) FROM noticias WHERE {date_col} IS NULL OR {date_col} = ''").fetchone()[0] or 0) if date_col else count
            missing_titles = int(con.execute(f"SELECT COUNT(*) FROM noticias WHERE {title_col} IS NULL OR {title_col} = ''").fetchone()[0] or 0) if title_col else count
            sources = [r[0] for r in con.execute(f"SELECT DISTINCT {source_col} FROM noticias WHERE {source_col} IS NOT NULL LIMIT 50").fetchall()] if source_col else []
            tickers = [r[0] for r in con.execute(f"SELECT DISTINCT {ticker_col} FROM noticias WHERE {ticker_col} IS NOT NULL LIMIT 200").fetchall()] if ticker_col else []
        status = "OK" if count else "EMPTY"
        if missing_dates or missing_titles:
            status = "WARNING" if count else status
        return make_audit_row(
            source_name="news_hunter",
            source_type="NEWS",
            primary_or_secondary="SECONDARY",
            expected_path_or_url=str(path),
            available=True,
            records_count=count,
            latest_date=str(latest or "")[:10],
            tickers_count=len(tickers),
            coverage_scope="noticias_locais",
            status=status,
            message=f"{count} noticias no News Hunter.",
            metadata={"sources": sources, "tickers": tickers, "missing_dates": missing_dates, "missing_titles": missing_titles},
        )
    except Exception as exc:
        return make_audit_row(source_name="news_hunter", source_type="NEWS", primary_or_secondary="SECONDARY", expected_path_or_url=str(path), status="ERROR", message=str(exc))


def audit_event_pipeline(db_path: str | Path | None = None) -> dict:
    cfg = load_config()
    path = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    if not path.exists():
        return make_audit_row(source_name="event_pipeline", source_type="NEWS", primary_or_secondary="DERIVED", expected_path_or_url=str(path), status="MISSING", message="Banco principal nao encontrado.")
    try:
        with sqlite3.connect(path) as con:
            events = 0
            links = 0
            latest = ""
            sources = []
            coverage_quality = ""
            tickers_count = 0
            if table_exists(con, "market_events"):
                events, latest, tickers_count = con.execute("SELECT COUNT(*), MAX(event_date), COUNT(DISTINCT ticker) FROM market_events").fetchone()
                try:
                    sources = [r[0] for r in con.execute("SELECT DISTINCT event_source FROM market_events WHERE event_source IS NOT NULL LIMIT 50").fetchall()]
                except Exception:
                    sources = []
            if table_exists(con, "signal_event_links"):
                links = int(con.execute("SELECT COUNT(*) FROM signal_event_links").fetchone()[0] or 0)
            if table_exists(con, "event_coverage_runs"):
                try:
                    coverage_quality = con.execute("SELECT coverage_quality FROM event_coverage_runs ORDER BY id DESC LIMIT 1").fetchone()
                    coverage_quality = coverage_quality[0] if coverage_quality else ""
                except Exception:
                    coverage_quality = ""
        status = "OK" if events else "EMPTY"
        if coverage_quality and "INSUFICIENTE" in str(coverage_quality).upper():
            status = "WARNING"
        return make_audit_row(
            source_name="event_pipeline",
            source_type="NEWS",
            primary_or_secondary="DERIVED",
            expected_path_or_url=str(path),
            available=True,
            records_count=events,
            latest_date=str(latest or "")[:10],
            tickers_count=int(tickers_count or 0),
            coverage_scope="market_events_signal_links",
            status=status,
            message=f"{events} eventos e {links} vinculos sinal-evento.",
            metadata={"links_count": links, "sources": sources, "coverage_quality": coverage_quality},
        )
    except Exception as exc:
        return make_audit_row(source_name="event_pipeline", source_type="NEWS", primary_or_secondary="DERIVED", expected_path_or_url=str(path), status="ERROR", message=str(exc))

