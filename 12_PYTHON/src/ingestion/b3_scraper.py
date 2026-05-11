"""
b3_scraper.py
-------------
Coleta preços históricos da B3 via yfinance e persiste em Parquet.

Lógica incremental:
  - Se o arquivo Parquet já existe, baixa apenas a partir do último dia salvo.
  - Se não existe, baixa desde start_date (default: 2019-01-01).

Formato do arquivo: data/raw/prices/{TICKER}.parquet
Schema:
  date (index), open, high, low, close, volume, adj_close

Uso:
    from src.ingestion.b3_scraper import B3Scraper, fetch_prices

    df = fetch_prices("BBAS3")
    df = fetch_prices("BBAS3", start_date="2020-01-01", force=True)
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.utils.errors import IngestionError
from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)

DEFAULT_START = "2019-01-01"
# yfinance espera sufixo .SA para ações da B3
_SA_SUFFIX = ".SA"


def _to_float_or_none(val) -> float | None:
    """Return None only if val is truly missing (None/NaN), not if it's zero.

    WR-04: avoids converting genuine 0.0 close prices (suspended sessions,
    penny stocks) to NULL. Only NaN and non-numeric values become None.
    """
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


class B3Scraper:
    """
    Busca e mantém série histórica de preços para tickers da B3.

    Args:
        output_dir: Diretório para salvar os Parquets (default: data/raw/prices/)
    """

    def __init__(self, output_dir: str | Path | None = None):
        if output_dir is None:
            from config.settings import settings

            output_dir = settings.data_raw / "prices"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── API pública ───────────────────────────────────────────────────────────

    def fetch(
        self,
        ticker: str,
        start_date: str | None = None,
        force: bool = False,
    ) -> pd.DataFrame:
        """
        Baixa preços históricos de um ticker de forma incremental.

        Se o Parquet local já existe e não está vazio, baixa apenas os dias
        faltantes a partir do último dado salvo.

        Args:
            ticker: Código de negociação sem sufixo (ex: "BBAS3")
            start_date: Data inicial no formato YYYY-MM-DD (usado só no primeiro download)
            force: True para re-baixar todo o histórico

        Returns:
            DataFrame completo (histórico acumulado) com índice DatetimeIndex
        """
        parquet_path = self.output_dir / f"{ticker.upper()}.parquet"
        existing = self._load_existing(parquet_path)

        if force or existing.empty:
            since = start_date or DEFAULT_START
            log.info(f"[{ticker}] Download completo desde {since}")
        else:
            last_date = existing.index.max().date()
            since = str(last_date + timedelta(days=1))
            today = date.today()
            if last_date >= today:
                log.info(f"[{ticker}] Preços já atualizados até {last_date}")
                return existing
            log.info(f"[{ticker}] Download incremental de {since} até hoje")

        new_data = self._download(ticker, since)

        if new_data.empty:
            log.warning(f"[{ticker}] Nenhum dado novo retornado pelo yfinance")
            return existing

        if not existing.empty and not force:
            combined = pd.concat([existing, new_data])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined.sort_index(inplace=True)
        else:
            combined = new_data

        combined.to_parquet(parquet_path)
        log.success(f"[{ticker}] {len(combined)} dias salvos em {parquet_path.name}")
        return combined

    def fetch_many(
        self,
        tickers: list[str],
        start_date: str | None = None,
        force: bool = False,
    ) -> dict[str, pd.DataFrame]:
        """Baixa preços de múltiplos tickers. Continua em caso de erro individual."""
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.fetch(ticker, start_date=start_date, force=force)
            except Exception as exc:
                log.error(f"[{ticker}] Falha ao buscar preços: {exc}")
                results[ticker] = pd.DataFrame()
        return results

    def load(self, ticker: str) -> pd.DataFrame:
        """Carrega Parquet local sem fazer requisição HTTP."""
        path = self.output_dir / f"{ticker.upper()}.parquet"
        return self._load_existing(path)

    # ── Internos ─────────────────────────────────────────────────────────────

    @retry(attempts=3, delay=3.0, backoff=2.0)
    def _download(self, ticker: str, since: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError:
            raise RuntimeError("yfinance não instalado — execute: pip install yfinance")

        symbol = ticker.upper() + _SA_SUFFIX
        raw = yf.download(
            symbol,
            start=since,
            end=str(date.today() + timedelta(days=1)),
            auto_adjust=True,
            progress=False,
        )

        if raw.empty:
            return pd.DataFrame()

        # Normalizar colunas (yfinance pode retornar MultiIndex)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw.columns = [c.lower().replace(" ", "_") for c in raw.columns]
        raw.index.name = "date"
        raw.index = pd.to_datetime(raw.index)

        expected = {"open", "high", "low", "close", "volume"}
        raw = raw[[c for c in raw.columns if c in expected]]

        return raw.dropna(how="all")

    def write_to_db(
        self,
        ticker: str,
        df: pd.DataFrame,
        conn: sqlite3.Connection,
    ) -> int:
        """Insert OHLCV rows into price_ohlcv table. Returns count of new rows inserted.
        Uses INSERT OR IGNORE — duplicate (ticker, date) rows skipped silently.
        Note: after yfinance auto_adjust=True, 'close' column contains adjusted close."""
        inserted = 0
        now = datetime.utcnow().isoformat()
        for dt, row in df.iterrows():
            date_str = (
                dt.date().isoformat()
                if hasattr(dt, "date")
                else str(dt)[:10]
            )
            cur = conn.execute(
                """INSERT OR IGNORE INTO price_ohlcv
                   (id, ticker, date, open, high, low, close, adj_close,
                    volume, is_gap, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (
                    str(uuid.uuid4()),
                    ticker,
                    date_str,
                    _to_float_or_none(row.get("open")),
                    _to_float_or_none(row.get("high")),
                    _to_float_or_none(row.get("low")),
                    _to_float_or_none(row.get("close")),
                    _to_float_or_none(row.get("close")),  # adj_close = auto-adjusted close
                    int(row.get("volume", 0) or 0) or None,
                    now,
                ),
            )
            inserted += cur.rowcount  # 1 on insert, 0 on OR IGNORE — reliable
        conn.commit()  # single commit after all rows
        return inserted

    def detect_and_insert_gaps(
        self,
        ticker: str,
        df: pd.DataFrame,
        start_date: str,
        conn: sqlite3.Connection,
    ) -> int:
        """Compare df.index against BMFBOVESPA calendar for start_date..today.
        Insert is_gap=1 rows for any missing trading day.
        Returns count of gap rows inserted. Never interpolates prices.
        start_date: ISO string 'YYYY-MM-DD'."""
        import pandas_market_calendars as mcal
        from datetime import date as date_type

        bmf = mcal.get_calendar("BMFBOVESPA")
        schedule = bmf.schedule(
            start_date=start_date,
            end_date=str(date_type.today()),
        )
        expected_dates = {
            ts.date() for ts in schedule.index
        }
        actual_dates = (
            {dt.date() for dt in df.index}
            if not df.empty
            else set()
        )
        gap_dates = expected_dates - actual_dates

        now = datetime.utcnow().isoformat()
        gaps_inserted = 0
        for gap_date in sorted(gap_dates):
            cur = conn.execute(
                """INSERT OR IGNORE INTO price_ohlcv
                   (id, ticker, date, is_gap, ingested_at)
                   VALUES (?, ?, ?, 1, ?)""",
                (str(uuid.uuid4()), ticker, gap_date.isoformat(), now),
            )
            gaps_inserted += cur.rowcount  # 1 on insert, 0 on OR IGNORE — reliable

        if gaps_inserted:
            log.warning(
                f"[{ticker}] {gaps_inserted} pregao(oes) sem dados — "
                f"marcados como GAP em price_ohlcv"
            )
        conn.commit()
        return gaps_inserted

    def fetch_and_store(
        self,
        ticker: str,
        conn: sqlite3.Connection,
        start_date: str = None,
    ) -> dict:
        """Incremental fetch + DB write + gap detection for one ticker.
        Returns {"inserted": int, "gaps": int, "ticker": str}."""
        # Incremental: use last stored date if no start_date given
        if start_date is None:
            row = conn.execute(
                "SELECT MAX(date) FROM price_ohlcv WHERE ticker = ? AND is_gap = 0",
                (ticker,),
            ).fetchone()
            if row and row[0]:
                # Start from day after last stored date
                last_d = datetime.fromisoformat(row[0]).date()
                since = str(last_d + timedelta(days=1))
            else:
                since = DEFAULT_START
        else:
            since = start_date

        try:
            df = self.fetch(ticker, start_date=since)
        except IngestionError as exc:
            log.error(f"[{ticker}] falha no fetch B3: {exc}")
            return {"inserted": 0, "gaps": 0, "ticker": ticker, "error": str(exc)}

        inserted = self.write_to_db(ticker, df, conn) if not df.empty else 0
        gaps = self.detect_and_insert_gaps(ticker, df, since, conn)
        log.info(f"[{ticker}] B3 — inserted={inserted} gaps={gaps}")
        return {"inserted": inserted, "gaps": gaps, "ticker": ticker}

    @staticmethod
    def _load_existing(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        try:
            df = pd.read_parquet(path)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as exc:
            log.warning(f"Não foi possível ler {path.name}: {exc}")
            return pd.DataFrame()


# ── Função de alto nível ──────────────────────────────────────────────────────


def fetch_prices(
    ticker: str,
    start_date: str | None = None,
    force: bool = False,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Atalho para B3Scraper().fetch() com configuração padrão."""
    return B3Scraper(output_dir=output_dir).fetch(ticker, start_date=start_date, force=force)
