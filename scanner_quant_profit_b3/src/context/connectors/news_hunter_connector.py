from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.context.event_model import EVENT_COLUMNS


DEFAULT_DB = Path(__file__).resolve().parents[4] / "12_PYTHON" / "news_hunter" / "banco.db"


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=EVENT_COLUMNS)


def load_events(start_date=None, end_date=None, tickers=None, db_path: str | Path | None = None) -> pd.DataFrame:
    path = Path(db_path) if db_path else DEFAULT_DB
    if not path.exists():
        return _empty()
    clauses = []
    params: list = []
    if start_date:
        clauses.append("date(COALESCE(data_pub, data_coleta)) >= date(?)")
        params.append(start_date)
    if end_date:
        clauses.append("date(COALESCE(data_pub, data_coleta)) <= date(?)")
        params.append(end_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with sqlite3.connect(path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='noticias'").fetchone()
            if not exists:
                return _empty()
            df = pd.read_sql_query(f"SELECT * FROM noticias {where} ORDER BY data_coleta DESC", con, params=params)
    except Exception:
        return _empty()
    rows = []
    clean_tickers = {ticker.upper() for ticker in tickers} if tickers else set()
    for _, row in df.iterrows():
        title = row.get("titulo") or ""
        content = row.get("conteudo") or row.get("resumo_curto") or ""
        matched_ticker = ""
        for ticker in clean_tickers:
            if ticker.lower() in f"{title} {content}".lower():
                matched_ticker = ticker
                break
        if clean_tickers and not matched_ticker:
            continue
        rows.append(
            {
                "event_date": pd.to_datetime(row.get("data_pub") or row.get("data_coleta"), errors="coerce").strftime("%Y-%m-%d"),
                "ticker": matched_ticker,
                "event_type": row.get("categoria") or "",
                "event_source": f"news_hunter:{row.get('fonte') or ''}".strip(":"),
                "event_title": title,
                "event_summary": content,
                "event_url": row.get("link"),
                "impact_score": min(1.0, max(0.0, float(row.get("score") or 0) / 10.0)),
                "confidence": 0.55,
                "metadata_json": {"news_hunter_id": row.get("id"), "subcategoria": row.get("subcategoria")},
            }
        )
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)

