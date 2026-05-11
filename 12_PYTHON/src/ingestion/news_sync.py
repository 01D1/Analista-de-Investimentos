"""
src/ingestion/news_sync.py
--------------------------
Cross-DB sync: reads articles from news_hunter/banco.db and
upserts into ingestion.db news_articles table.

D-01/D-03: news_hunter/ internals are NOT modified. banco.db stays separate.
This module is READ-ONLY with respect to banco.db.
ING-06: URL-based deduplication via INSERT OR IGNORE + UNIQUE INDEX.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)

# Path to news_hunter's SQLite database (D-03: stays separate from ingestion.db)
BANCO_DB = Path(__file__).parent.parent.parent / "news_hunter" / "banco.db"

# B3 ticker pattern: 4 uppercase letters + 1-2 digits (e.g. PETR4, SANB11)
_B3_TICKER_RE = re.compile(r"^[A-Z]{4}[0-9]{1,2}$")


def _is_b3_ticker(value: str) -> bool:
    """Return True if value looks like a B3 ticker code."""
    if not value:
        return False
    return bool(_B3_TICKER_RE.match(value.strip().upper()))


def sync_news_to_ingestion_db(
    ingestion_conn: sqlite3.Connection,
    limit: int = 500,
    banco_db_path: Path = BANCO_DB,
) -> int:
    """Read up to `limit` recent articles from banco.db and upsert into news_articles.

    Uses INSERT OR IGNORE against the UNIQUE INDEX on url — deduplicates automatically.
    Returns count of new rows inserted (not total rows read).

    Safe when banco.db does not exist — logs WARNING and returns 0.
    READ-ONLY access to banco.db — never writes to it.
    """
    if not banco_db_path.exists():
        log.warning(
            f"[news_sync] banco.db não encontrado: {banco_db_path} — "
            "nenhum artigo sincronizado"
        )
        return 0

    try:
        with sqlite3.connect(banco_db_path) as src:
            src.row_factory = sqlite3.Row
            rows = src.execute(
                """SELECT hash, titulo, link, fonte, categoria, data_pub, score
                   FROM noticias
                   ORDER BY data_coleta DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        log.error(f"[news_sync] erro ao ler banco.db: {exc}")
        return 0

    inserted = 0
    now = datetime.utcnow().isoformat()

    for row in rows:
        url = str(row["link"] or "").strip()
        if not url:
            continue

        title = str(row["titulo"] or "").strip()
        if not title:
            continue

        # D-05 / Open Question 2: store categoria as ticker_tags if it matches B3 pattern
        # Full cross-tagging with tickers.yaml deferred to Phase 4
        categoria = str(row["categoria"] or "").strip()
        ticker_tags: str | None = None
        if _is_b3_ticker(categoria):
            ticker_tags = json.dumps([categoria.upper()])

        try:
            score = int(row["score"] or 0)
        except (ValueError, TypeError):
            score = 0

        cur = ingestion_conn.execute(
            """INSERT OR IGNORE INTO news_articles
               (id, url, title, published_at, source, ticker_tags, score, ingested_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                url,
                title,
                str(row["data_pub"] or "").strip() or None,
                str(row["fonte"] or "").strip() or None,
                ticker_tags,
                score,
                now,
            ),
        )
        inserted += cur.rowcount  # 1 on insert, 0 on OR IGNORE — reliable

    ingestion_conn.commit()
    log.info(f"[news_sync] sincronizados {inserted} novos artigos de {len(rows)} lidos")
    return inserted
