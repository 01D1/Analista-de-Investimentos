"""
processing/storage.py
---------------------
Leitura e consulta dos dados já processados em data/processed/.

Não faz parsing — apenas lê os JSONs/Parquets salvos pelo pipeline.

Uso:
    from src.processing.storage import ProcessedStore

    store = ProcessedStore()
    years = store.available_years("BBAS3")     # [2019, 2020, ..., 2024]
    data  = store.load("BBAS3", 2024)          # dict com statements
    df    = store.load_all("BBAS3")            # DataFrame com séries históricas
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)


class ProcessedStore:
    """
    Interface de leitura para dados processados.

    Args:
        processed_dir: Raiz de data/processed/ (default: via settings)
    """

    def __init__(self, processed_dir: Path | None = None):
        if processed_dir is None:
            from config.settings import settings

            processed_dir = settings.data_processed
        self.base = processed_dir

    # ── Consultas ─────────────────────────────────────────────────────────────

    def available_years(self, ticker: str) -> list[int]:
        """Retorna anos que já têm dados processados."""
        ticker_dir = self.base / ticker.upper()
        if not ticker_dir.exists():
            return []
        years = []
        for f in ticker_dir.glob("dfp_*.json"):
            try:
                years.append(int(f.stem.split("_")[1]))
            except (IndexError, ValueError):
                pass
        return sorted(years)

    def missing_years(self, ticker: str, years: list[int]) -> list[int]:
        """Retorna quais anos ainda não foram processados."""
        done = set(self.available_years(ticker))
        return [y for y in years if y not in done]

    def load(self, ticker: str, year: int) -> dict | None:
        """Carrega os dados processados de um ticker/ano como dict."""
        path = self.base / ticker.upper() / f"dfp_{year}.json"
        if not path.exists():
            log.warning(f"[{ticker}] {year}: dados processados não encontrados")
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error(f"[{ticker}] {year}: erro ao ler {path.name}: {exc}")
            return None

    def load_all(self, ticker: str) -> dict[int, dict]:
        """Carrega todos os anos disponíveis para um ticker."""
        years = self.available_years(ticker)
        result = {}
        for year in years:
            data = self.load(ticker, year)
            if data is not None:
                result[year] = data
        return result

    def status(self, tickers: list[str] | None = None) -> pd.DataFrame:
        """
        Retorna DataFrame com status de processamento por ticker/ano.

        Colunas: ticker, year, has_data
        """
        if tickers is None:
            from config.settings import settings

            tickers = settings.active_tickers

        rows = []
        for ticker in tickers:
            years = self.available_years(ticker)
            if not years:
                rows.append({"ticker": ticker, "years_processed": 0, "years": ""})
            else:
                rows.append(
                    {
                        "ticker": ticker,
                        "years_processed": len(years),
                        "years": ", ".join(str(y) for y in years),
                    }
                )

        return pd.DataFrame(rows)

    def summary_table(self, ticker: str) -> pd.DataFrame | None:
        """
        Constrói uma tabela resumida de DRE para séries históricas (bancos).
        Retorna DataFrame com anos como colunas e métricas como linhas.
        """
        all_data = self.load_all(ticker)
        if not all_data:
            return None

        rows = []
        for year, data in sorted(all_data.items()):
            inc = data.get("income_statement", {})
            bal = data.get("balance_sheet", {})
            assets = bal.get("assets", {}) if bal else {}
            liab = bal.get("liabilities", {}) if bal else {}
            row = {"year": year}
            for field in [
                "total_financial_revenues",
                "nii_gross",
                "net_income",
                "total_financial_expenses",
                "loan_loss_provision",
            ]:
                row[field] = inc.get(field)
            row["total_assets"] = assets.get("total_assets")
            row["shareholders_equity"] = liab.get("shareholders_equity")
            rows.append(row)

        return pd.DataFrame(rows).set_index("year")
