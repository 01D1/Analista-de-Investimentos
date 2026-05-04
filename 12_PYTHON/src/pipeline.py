"""
pipeline.py
-----------
Orquestrador principal do pipeline de inteligência financeira.

Responsabilidades:
  1. Coordenar extração de DFPs (industriais e bancos) via parsers
  2. Calcular métricas financeiras
  3. Detectar inconsistências
  4. Avaliar qualidade dos lucros
  5. Exportar dados em múltiplos formatos (JSON, CSV, Excel, Markdown)

Uso rápido:
    from pipeline import Pipeline, PipelineConfig

    config = PipelineConfig(
        raw_dir=Path("data/raw/cvm/DFP"),
        output_dir=Path("data/processed"),
        tickers=["WEGE3", "ITUB4", "BBAS3"],
        years=range(2019, 2026),
    )
    pipeline = Pipeline(config)
    pipeline.run()
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


@dataclass
class PipelineConfig:
    """Configuração do pipeline."""

    raw_dir: Path  # diretório raiz com subpastas por ano
    output_dir: Path  # diretório de saída
    tickers: list[str]  # tickers a processar
    years: range | list[int] = field(default_factory=lambda: range(2019, 2026))
    consolidation: str = "con"  # "con" ou "ind"
    detect_inconsistencies: bool = True
    evaluate_earnings_quality: bool = True
    export_json: bool = True
    export_csv: bool = True
    export_excel: bool = False  # requer openpyxl
    export_markdown: bool = True
    log_level: str = "INFO"

    def __post_init__(self):
        self.raw_dir = Path(self.raw_dir)
        self.output_dir = Path(self.output_dir)
        self.years = list(self.years)


# ---------------------------------------------------------------------------
# Resultado por empresa/ano
# ---------------------------------------------------------------------------


@dataclass
class ExtractionResult:
    """Resultado da extração de um ticker/ano."""

    ticker: str
    year: int
    success: bool
    is_bank: bool
    statements: object | None = None  # FinancialStatements ou BankStatements
    inconsistencies: object | None = None
    earnings_quality: object | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        d = {"ticker": self.ticker, "year": self.year, "success": self.success}
        if self.error:
            d["error"] = self.error
        return d


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


class Pipeline:
    """
    Orquestrador principal do pipeline de inteligência financeira.

    Exemplo de uso:
        pipeline = Pipeline(config)
        results = pipeline.run()
        pipeline.export(results)
    """

    # Tickers de industriais (não-bancos)
    INDUSTRIAL_TICKERS = {"WEGE3"}

    # Bancos — importar do registry do bank_parser
    from parsers.bank_parser import BANK_REGISTRY as _BANK_REGISTRY  # type: ignore

    BANK_TICKERS = set(_BANK_REGISTRY.keys()) if _BANK_REGISTRY else set()

    def __init__(self, config: PipelineConfig):
        self.config = config
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format="%(levelname)s | %(message)s",
        )
        self._setup_parsers()

    def _setup_parsers(self):
        """Inicializa parsers industriais e de bancos."""
        try:
            from parsers.bank_parser import BankParser
            from parsers.dfp_parser import DFPParser

            self._industrial_parser = DFPParser()
            self._bank_parser = BankParser()
        except ImportError as e:
            logger.warning(f"Não foi possível importar parsers: {e}")
            self._industrial_parser = None
            self._bank_parser = None

    def run(self) -> list[ExtractionResult]:
        """
        Executa o pipeline para todos os tickers e anos configurados.

        Returns:
            Lista de ExtractionResult — um por (ticker, year)
        """
        results = []
        config = self.config

        for ticker in config.tickers:
            logger.info(f"Processando {ticker}...")
            for year in config.years:
                result = self._process_one(ticker, year)
                results.append(result)
                if result.success:
                    logger.debug(f"  {ticker} {year}: OK")
                else:
                    logger.warning(f"  {ticker} {year}: FALHOU — {result.error}")

        logger.info(
            f"Pipeline concluído: {sum(r.success for r in results)}/{len(results)} extrações bem-sucedidas"
        )
        return results

    def _process_one(self, ticker: str, year: int) -> ExtractionResult:
        """Processa um único ticker/ano."""
        is_bank = ticker in self.BANK_TICKERS
        raw_dir = self.config.raw_dir / str(year)

        try:
            if is_bank:
                return self._process_bank(ticker, year, raw_dir)
            else:
                return self._process_industrial(ticker, year, raw_dir)
        except Exception as e:
            logger.error(f"{ticker} {year}: erro inesperado — {e}", exc_info=True)
            return ExtractionResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=is_bank,
                error=str(e),
            )

    def _process_industrial(self, ticker: str, year: int, raw_dir: Path) -> ExtractionResult:
        """Extrai e processa empresa industrial."""
        if self._industrial_parser is None:
            return ExtractionResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=False,
                error="DFPParser não disponível",
            )

        # Para industriais, buscar o código CVM via mapeamento separado
        # (por ora, WEGE3 está hardcoded como exemplo)
        INDUSTRIAL_CVM = {"WEGE3": "005410"}
        cvm_code = INDUSTRIAL_CVM.get(ticker)
        if not cvm_code:
            return ExtractionResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=False,
                error=f"CVM code desconhecido para {ticker}",
            )

        dfs = self._industrial_parser.parse_company(
            cvm_code=cvm_code,
            raw_dir=raw_dir,
            consolidation=self.config.consolidation,
        )
        if not dfs:
            return ExtractionResult(
                ticker=ticker, year=year, success=False, is_bank=False, error="Sem dados no CSV CVM"
            )

        return ExtractionResult(
            ticker=ticker,
            year=year,
            success=True,
            is_bank=False,
            statements=dfs,
        )

    def _process_bank(self, ticker: str, year: int, raw_dir: Path) -> ExtractionResult:
        """Extrai e processa banco."""
        if self._bank_parser is None:
            return ExtractionResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=True,
                error="BankParser não disponível",
            )

        stmts = self._bank_parser.parse(
            ticker=ticker,
            year=year,
            raw_dir=raw_dir,
            consolidation=self.config.consolidation,
        )
        if stmts is None:
            return ExtractionResult(
                ticker=ticker,
                year=year,
                success=False,
                is_bank=True,
                error="BankParser retornou None",
            )

        # Verificação de inconsistências (opcional)
        inconsistencies = None
        if self.config.detect_inconsistencies:
            try:
                from analysis.detect_inconsistencies import BankInconsistencyDetector

                detector = BankInconsistencyDetector()
                inc = stmts.income_statement
                assets = stmts.balance_sheet.assets
                liabilities = stmts.balance_sheet.liabilities
                inconsistencies = detector.check(
                    ticker=ticker,
                    year=year,
                    income=inc.__dict__ if inc else {},
                    assets=assets.__dict__ if assets else {},
                    liabilities=liabilities.__dict__ if liabilities else {},
                    cashflow=stmts.cash_flow.__dict__ if stmts.cash_flow else None,
                )
                if not inconsistencies.is_clean:
                    for err in inconsistencies.errors:
                        logger.warning(f"  {ticker} {year}: {err.code} — {err.description}")
            except Exception as e:
                logger.debug(f"  {ticker} {year}: erro no detector de inconsistências — {e}")

        return ExtractionResult(
            ticker=ticker,
            year=year,
            success=True,
            is_bank=True,
            statements=stmts,
            inconsistencies=inconsistencies,
        )

    # ---------------------------------------------------------------------------
    # Export
    # ---------------------------------------------------------------------------

    def export(self, results: list[ExtractionResult]) -> None:
        """Exporta resultados em todos os formatos configurados."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.export_json:
            self._export_json(results)
        if self.config.export_csv:
            self._export_csv(results)
        if self.config.export_excel:
            self._export_excel(results)

    def _export_json(self, results: list[ExtractionResult]) -> None:
        """Exporta todos os resultados em JSON."""
        out = {}
        for r in results:
            if not r.success:
                continue
            key = f"{r.ticker}_{r.year}"
            if r.is_bank and hasattr(r.statements, "model_dump"):
                out[key] = r.statements.model_dump()
            elif r.statements:
                out[key] = str(r.statements)

        path = self.config.output_dir / "results.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        logger.info(f"JSON exportado: {path}")

    def _export_csv(self, results: list[ExtractionResult]) -> None:
        """Exporta tabela resumida em CSV."""
        import csv

        rows = []
        for r in results:
            if not r.success:
                continue
            row = {"ticker": r.ticker, "year": r.year}
            if r.is_bank and r.statements:
                stmts = r.statements
                inc = stmts.income_statement
                bal = stmts.balance_sheet
                row.update(
                    {
                        "total_revenues": getattr(inc, "total_financial_revenues", None),
                        "nii_gross": getattr(inc, "nii_gross", None),
                        "net_income": getattr(inc, "net_income", None),
                        "total_assets": getattr(bal.assets, "total_assets", None)
                        if bal.assets
                        else None,
                        "shareholders_equity": getattr(bal.liabilities, "shareholders_equity", None)
                        if bal.liabilities
                        else None,
                    }
                )
            rows.append(row)

        if not rows:
            return

        path = self.config.output_dir / "results_summary.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"CSV exportado: {path}")

    def _export_excel(self, results: list[ExtractionResult]) -> None:
        """Exporta Excel com múltiplas abas por tipo de dado."""
        try:
            import openpyxl
        except ImportError:
            logger.error("openpyxl não instalado — instalar com: pip install openpyxl")
            return

        wb = openpyxl.Workbook()
        # Planilha de resultados gerais
        ws = wb.active
        ws.title = "Resumo"

        bank_results = [
            (r.ticker, r.year, r.statements)
            for r in results
            if r.success and r.is_bank and r.statements
        ]

        if bank_results:
            # Cabeçalho
            headers = [
                "Ticker",
                "Ano",
                "Receitas Intermediação",
                "NII Bruto",
                "Lucro Líquido",
                "Total Ativos",
                "PL",
                "ROE %",
            ]
            ws.append(headers)

            for ticker, year, stmts in bank_results:
                inc = stmts.income_statement
                bal = stmts.balance_sheet
                se = getattr(bal.liabilities, "shareholders_equity", 0) if bal.liabilities else 0
                ni = getattr(inc, "net_income", 0) or 0
                roe = (ni / se * 100) if se > 0 else None
                ws.append(
                    [
                        ticker,
                        year,
                        getattr(inc, "total_financial_revenues", None),
                        getattr(inc, "nii_gross", None),
                        ni,
                        getattr(bal.assets, "total_assets", None) if bal.assets else None,
                        se,
                        round(roe, 1) if roe else None,
                    ]
                )

        path = self.config.output_dir / "resultados.xlsx"
        wb.save(path)
        logger.info(f"Excel exportado: {path}")


# ---------------------------------------------------------------------------
# Entrypoint rápido
# ---------------------------------------------------------------------------


def run_full_pipeline(
    raw_dir: str = "data/raw/cvm/DFP",
    output_dir: str = "data/processed",
    tickers: list[str] | None = None,
    years: list[int] | None = None,
    export_excel: bool = False,
) -> list[ExtractionResult]:
    """
    Roda o pipeline completo com configuração mínima.

    Args:
        raw_dir: diretório raiz com subpastas por ano dos CSVs CVM
        output_dir: diretório de saída para arquivos exportados
        tickers: lista de tickers (default: todos os bancos + WEGE3)
        years: anos a processar (default: 2019–2025)
        export_excel: True para gerar .xlsx (requer openpyxl)

    Returns:
        Lista de ExtractionResult
    """
    if tickers is None:
        from parsers.bank_parser import BANK_REGISTRY

        tickers = list(BANK_REGISTRY.keys()) + ["WEGE3"]

    if years is None:
        years = list(range(2019, 2026))

    config = PipelineConfig(
        raw_dir=Path(raw_dir),
        output_dir=Path(output_dir),
        tickers=tickers,
        years=years,
        export_excel=export_excel,
    )

    pipeline = Pipeline(config)
    results = pipeline.run()
    pipeline.export(results)
    return results


if __name__ == "__main__":
    import sys

    results = run_full_pipeline()
    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n{len(failed)} extração(ões) falharam:")
        for r in failed:
            print(f"  {r.ticker} {r.year}: {r.error}")
    sys.exit(0 if not failed else 1)
