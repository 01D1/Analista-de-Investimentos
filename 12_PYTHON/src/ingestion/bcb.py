"""
src/ingestion/bcb.py
--------------------
BCB SGS macro series ingestion — ING-04.
Fetches Selic, IPCA, PTAX, CDS Brasil, PIB from BCB SGS API.
All external calls wrapped with @retry from Phase 1 infrastructure.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from datetime import date, datetime
from pathlib import Path

import requests

from src.utils.errors import IngestionError
from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)

# BCB SGS endpoint — no auth required (public API)
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"

# D-11: exact series to ingest (VERIFIED live 2026-05-10)
BCB_SERIES: dict[str, int] = {
    "selic_over":   11,
    "ipca_12m":    433,
    "ptax_usd":      1,
    "cds_brasil": 29039,   # pontos-base: divide by 10,000 before storing
    "pib_nominal":  4380,
}

# Series whose raw values are in basis points and must be divided by 10,000
_BP_SERIES = {29039}

# Courtesy rate limit between sequential series calls (BCB soft rate limit)
_INTER_SERIES_SLEEP = 0.5


@retry(
    attempts=3,
    delay=2.0,
    backoff=2.0,
    jitter=0.5,
    exceptions=(requests.RequestException,),
)
def fetch_series(cod: int, inicio: str = "01/01/2019") -> list[dict]:
    """Fetch a BCB SGS series. Returns list of {'data': 'dd/mm/yyyy', 'valor': str}.
    Raises IngestionError after 3 failed attempts."""
    fim = datetime.now().strftime("%d/%m/%Y")
    url = BCB_SGS_URL.format(cod=cod)
    params = {
        "formato": "json",
        "dataInicial": inicio,
        "dataFinal": fim,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_last_date_for_series(conn: sqlite3.Connection, series_code: int) -> str:
    """Return 'dd/mm/yyyy' for the most recent stored date, or '01/01/2019'."""
    row = conn.execute(
        "SELECT MAX(date) FROM macro_series WHERE series_code = ?",
        (series_code,),
    ).fetchone()
    if row and row[0]:
        d = datetime.fromisoformat(row[0])
        return d.strftime("%d/%m/%Y")
    return "01/01/2019"


def is_stale(last_date: date, threshold_days: int = 1) -> bool:
    """Return True if last_date is more than threshold_days BMFBOVESPA business days ago.
    D-12: stale threshold = 1 business day."""
    try:
        import pandas_market_calendars as mcal
        bmf = mcal.get_calendar("BMFBOVESPA")
        schedule = bmf.schedule(
            start_date=str(last_date),
            end_date=str(date.today()),
        )
        # Number of trading days between last_date (exclusive) and today (inclusive)
        trading_days = max(0, len(schedule) - 1)
        return trading_days > threshold_days
    except Exception as exc:
        log.warning(f"[bcb] freshness check falhou: {exc} — assumindo não-stale")
        return False


def ingest_all_series(conn: sqlite3.Connection) -> dict:
    """Fetch all 5 BCB series incrementally and upsert into macro_series.

    Returns dict: {"inserted": int, "updated": int, "failed": list[str],
                    "stale": list[str], "last_ingested_at": str}
    """
    inserted = 0
    failed: list[str] = []
    stale: list[str] = []
    now = datetime.utcnow().isoformat()

    for series_name, series_code in BCB_SERIES.items():
        inicio = get_last_date_for_series(conn, series_code)

        # D-12: check freshness before fetching
        try:
            last_iso = conn.execute(
                "SELECT MAX(date) FROM macro_series WHERE series_code = ?",
                (series_code,),
            ).fetchone()[0]
            if last_iso:
                last_d = datetime.fromisoformat(last_iso).date()
                if is_stale(last_d):
                    stale.append(series_name)
                    log.warning(
                        f"[bcb] serie {series_name} ({series_code}) esta stale — "
                        f"ultimo dado: {last_iso}"
                    )
        except Exception as exc:
            log.debug(f"[bcb] freshness check ignorado: {exc}")

        try:
            rows = fetch_series(series_code, inicio=inicio)
        except IngestionError as exc:
            log.error(f"[bcb] falha ao buscar {series_name}: {exc}")
            failed.append(series_name)
            continue

        for item in rows:
            try:
                raw_val = float(str(item["valor"]).replace(",", "."))
            except (ValueError, TypeError):
                log.warning(f"[bcb] valor invalido em {series_name}: {item}")
                continue

            # D-11 note: CDS Brasil in basis points → convert to decimal
            value = raw_val / 10_000 if series_code in _BP_SERIES else raw_val

            # Parse 'dd/mm/yyyy' → ISO 'YYYY-MM-DD'
            try:
                d = datetime.strptime(item["data"], "%d/%m/%Y")
                iso_date = d.strftime("%Y-%m-%d")
            except ValueError:
                log.warning(f"[bcb] data invalida em {series_name}: {item['data']}")
                continue

            conn.execute(
                """INSERT OR IGNORE INTO macro_series
                   (id, series_code, series_name, date, value, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), series_code, series_name, iso_date, value, now),
            )
            inserted += conn.execute("SELECT changes()").fetchone()[0]

        conn.commit()
        log.info(f"[bcb] {series_name} — {len(rows)} pontos buscados")
        time.sleep(_INTER_SERIES_SLEEP)

    return {
        "inserted": inserted,
        "updated": 0,   # INSERT OR IGNORE: no updates, only new rows
        "failed": failed,
        "stale": stale,
        "last_ingested_at": now,
    }
