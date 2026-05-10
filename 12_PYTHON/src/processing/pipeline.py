"""
processing/pipeline.py
-----------------------
Orquestrador automático: raw CSVs da CVM → dados processados e validados.

Fluxo por (ticker, year):
  1. Verificar se já processado (data/processed/{ticker}/dfp_{year}.json)
  2. Localizar CSVs em data/raw/cvm/DFP/{year}/
  3. Rotear para parser correto (bank vs industrial) via tickers.yaml
  4. Validar: BP fecha? DFC coerente? Sem duplicatas?
  5. Salvar em data/processed/{ticker}/
  6. Alertar sobre falhas (nunca descartar silenciosamente)

Uso:
    from src.processing.pipeline import process_ticker

    result = process_ticker("BBAS3", years=range(2019, 2026))
    result = process_ticker("WEGE3", years=[2024], force=True)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logger import get_logger

log = get_logger(__name__)

# ── Tipos ─────────────────────────────────────────────────────────────────────


@dataclass
class PeriodResult:
    ticker: str
    year: int
    success: bool
    is_bank: bool
    skipped: bool = False  # já estava processado
    alerts: list[str] = field(default_factory=list)
    error: str | None = None
    output_path: Path | None = None

    def log_summary(self) -> None:
        status = "OK" if self.success else ("PULADO" if self.skipped else "FALHA")
        log.info(
            f"[{self.ticker}] {self.year}: {status}" + (f" — {self.error}" if self.error else "")
        )
        for alert in self.alerts:
            log.warning(f"[{self.ticker}] {self.year} ALERTA: {alert}")


@dataclass
class ProcessingResult:
    ticker: str
    total: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    periods: list[PeriodResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        processed = self.total - self.skipped
        return self.succeeded / processed if processed else 0.0


# ── Pipeline principal ────────────────────────────────────────────────────────


class ProcessingPipeline:
    """
    Pipeline raw → processed para um ticker.

    Args:
        raw_cvm_dir: Raiz dos CSVs CVM (data/raw/cvm/)
        processed_dir: Raiz dos dados processados (data/processed/)
        consolidation: "con" (consolidado) ou "ind" (controladora)
    """

    def __init__(
        self,
        raw_cvm_dir: Path | None = None,
        processed_dir: Path | None = None,
        consolidation: str = "con",
    ):
        from config.settings import settings

        self.raw_cvm_dir = raw_cvm_dir or (settings.data_raw / "cvm")
        self.processed_dir = processed_dir or settings.data_processed
        self.consolidation = consolidation
        self._ticker_registry = self._load_registry()

    def run(
        self,
        ticker: str,
        years: list[int] | None = None,
        force: bool = False,
    ) -> ProcessingResult:
        """Processa um ticker para todos os anos especificados."""
        if years is None:
            years = list(range(2019, date.today().year + 1))

        info = self._ticker_registry.get(ticker.upper())
        if not info:
            log.error(f"[{ticker}] não encontrado em tickers.yaml")
            return ProcessingResult(ticker=ticker)

        cvm_code = self._get_cvm_code(ticker)
        is_bank = info.get("type") == "bank"

        result = ProcessingResult(ticker=ticker, total=len(years))
        log.info(f"[{ticker}] processando {len(years)} anos (banco={is_bank}, CVM={cvm_code})")

        for year in years:
            period_result = self._process_year(
                ticker=ticker,
                year=year,
                cvm_code=cvm_code,
                is_bank=is_bank,
                force=force,
            )
            period_result.log_summary()
            result.periods.append(period_result)

            if period_result.skipped:
                result.skipped += 1
            elif period_result.success:
                result.succeeded += 1
            else:
                result.failed += 1

        log.info(
            f"[{ticker}] concluído — "
            f"ok={result.succeeded} pulados={result.skipped} falhas={result.failed}"
        )
        return result

    # ── Processamento por ano ─────────────────────────────────────────────────

    def _process_year(
        self,
        ticker: str,
        year: int,
        cvm_code: str,
        is_bank: bool,
        force: bool,
    ) -> PeriodResult:
        output_path = self.processed_dir / ticker / f"dfp_{year}.json"

        if output_path.exists() and not force:
            return PeriodResult(
                ticker=ticker,
                year=year,
                success=True,
                is_bank=is_bank,
                skipped=True,
                output_path=output_path,
            )

        raw_dir = self.raw_cvm_dir / "DFP" / str(year)
        if not raw_dir.exists() or not list(raw_dir.glob("*.csv")):
            return PeriodResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=is_bank,
                error=f"CSVs não encontrados em {raw_dir} — execute 'ingest' primeiro",
            )

        try:
            if is_bank:
                return self._process_bank(ticker, year, cvm_code, raw_dir, output_path)
            else:
                return self._process_industrial(ticker, year, cvm_code, raw_dir, output_path)
        except Exception as exc:
            log.error(f"[{ticker}] {year}: erro inesperado — {exc}", exc_info=True)
            return PeriodResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=is_bank,
                error=str(exc),
            )

    def _process_bank(
        self,
        ticker: str,
        year: int,
        cvm_code: str,
        raw_dir: Path,
        output_path: Path,
    ) -> PeriodResult:
        from src.analysis.detect_inconsistencies import BankInconsistencyDetector
        from src.parsers.bank_parser import BankParser

        parser = BankParser()
        stmts = parser.parse(
            ticker=ticker,
            year=year,
            raw_dir=raw_dir,
            consolidation=self.consolidation,
        )

        if stmts is None:
            return PeriodResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=True,
                error="BankParser retornou None — dados ausentes no CSV",
            )

        alerts: list[str] = []

        # Validação de inconsistências
        try:
            detector = BankInconsistencyDetector()
            inc = stmts.income_statement
            assets = stmts.balance_sheet.assets if stmts.balance_sheet else None
            liabilities = stmts.balance_sheet.liabilities if stmts.balance_sheet else None
            report = detector.check(
                ticker=ticker,
                year=year,
                income=inc.__dict__ if inc else {},
                assets=assets.__dict__ if assets else {},
                liabilities=liabilities.__dict__ if liabilities else {},
                cashflow=stmts.cash_flow.__dict__ if stmts.cash_flow else None,
            )
            if not report.is_clean:
                for err in report.errors:
                    alerts.append(f"{err.code}: {err.description}")
        except Exception as exc:
            alerts.append(f"Validação não executada: {exc}")

        self._save(stmts, output_path)
        return PeriodResult(
            ticker=ticker,
            year=year,
            success=True,
            is_bank=True,
            alerts=alerts,
            output_path=output_path,
        )

    def _process_industrial(
        self,
        ticker: str,
        year: int,
        cvm_code: str,
        raw_dir: Path,
        output_path: Path,
    ) -> PeriodResult:
        from src.parsers.dfp_parser import DFPParser

        parser = DFPParser()
        dfs = parser.parse_company(
            cvm_code=cvm_code,
            raw_dir=raw_dir,
            consolidation=self.consolidation,
        )

        if not dfs:
            return PeriodResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=False,
                error="DFPParser sem dados — verifique o código CVM",
            )

        alerts: list[str] = []

        # Validação básica: BP deve fechar (BPA total = BPP total)
        if "BPA" in dfs and "BPP" in dfs:
            total_assets = self._sum_root(dfs["BPA"], "1")
            total_liab_eq = self._sum_root(dfs["BPP"], "2")
            if total_assets and total_liab_eq:
                diff = abs(total_assets - total_liab_eq)
                tolerance = abs(total_assets) * 0.02
                if diff > tolerance:
                    alerts.append(
                        f"BP não fecha: Ativo={total_assets:,.0f} vs "
                        f"Passivo+PL={total_liab_eq:,.0f} (diff={diff:,.0f})"
                    )

        # Persistir como dict de DataFrames serializado
        data = {k: v.to_dict(orient="records") for k, v in dfs.items()}
        self._save_dict(data, output_path)

        return PeriodResult(
            ticker=ticker,
            year=year,
            success=True,
            is_bank=False,
            alerts=alerts,
            output_path=output_path,
        )

    # ── Persistência ─────────────────────────────────────────────────────────

    def _save(self, obj: Any, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        elif hasattr(obj, "__dict__"):
            data = obj.__dict__
        else:
            data = str(obj)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def _save_dict(self, data: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sum_root(df: pd.DataFrame, prefix: str) -> float | None:
        if "account_code" not in df.columns or "value" not in df.columns:
            return None
        mask = df["account_code"].astype(str).str.match(rf"^{prefix}$")
        vals = df.loc[mask, "value"].dropna()
        return float(vals.iloc[0]) if not vals.empty else None

    @staticmethod
    def _load_registry() -> dict:
        from config.settings import settings

        return {t["ticker"]: t for t in settings.tickers}

    @staticmethod
    def _get_cvm_code(ticker: str) -> str:
        from src.ingestion.cvm_downloader import get_cvm_code

        return get_cvm_code(ticker)


# ── Função de alto nível ──────────────────────────────────────────────────────


def process_ticker(
    ticker: str,
    years: list[int] | None = None,
    force: bool = False,
    consolidation: str = "con",
) -> ProcessingResult:
    """
    Processa um ticker de ponta a ponta: raw → validado → persistido.

    Args:
        ticker: Código de negociação (ex: "BBAS3")
        years: Anos a processar (default: 2019 até ano corrente)
        force: True para reprocessar mesmo se arquivo já existir
        consolidation: "con" (consolidado) ou "ind" (controladora)

    Returns:
        ProcessingResult com resumo e detalhes por período
    """
    pipeline = ProcessingPipeline(consolidation=consolidation)
    return pipeline.run(ticker, years=years, force=force)
