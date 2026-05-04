"""
cvm_downloader.py
-----------------
Baixa dados financeiros da CVM (Comissão de Valores Mobiliários)
via portal de dados abertos: https://dados.cvm.gov.br/

Documentos suportados:
  - DFP (Demonstração Financeira Padronizada — anual)
  - ITR (Informações Trimestrais)

A CVM distribui os dados como ZIPs contendo CSVs de todas as companhias
abertas. O filtro por ticker é feito no momento do parse (via CD_CVM).

Uso:
    from src.ingestion.cvm_downloader import CVMDownloader, ingest_ticker

    # Download de um ano
    dl = CVMDownloader()
    dl.download_dfp(2024)

    # Ingestão incremental por ticker (recomendado)
    result = ingest_ticker("BBAS3", doc_types=["DFP", "ITR"], years=range(2019, 2026))
"""

from __future__ import annotations

import io
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Literal

import requests
import yaml

from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)

BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
RATE_LIMIT_SECONDS = 1.5
DocType = Literal["DFP", "ITR"]

_CVM_CODES: dict[str, str] | None = None


def _load_cvm_codes() -> dict[str, str]:
    global _CVM_CODES
    if _CVM_CODES is None:
        path = Path(__file__).parent.parent.parent / "config" / "cvm_codes.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        _CVM_CODES = data.get("cvm_codes", {})
    return _CVM_CODES


def get_cvm_code(ticker: str) -> str:
    """Retorna o CD_CVM de um ticker. Lança KeyError se não mapeado."""
    codes = _load_cvm_codes()
    code = codes.get(ticker.upper())
    if not code:
        raise KeyError(
            f"Ticker '{ticker}' não encontrado em config/cvm_codes.yaml. "
            "Adicione o CD_CVM manualmente."
        )
    return str(code).zfill(6)


# ── Downloader ────────────────────────────────────────────────────────────────


class CVMDownloader:
    """
    Baixa e extrai arquivos de dados abertos da CVM.

    Os ZIPs são compartilhados entre todas as empresas — o filtro por ticker
    ocorre no parse. Esta classe apenas garante que os arquivos estejam locais.

    Args:
        output_dir: Diretório base (default: data/raw/cvm/)
        timeout: Timeout HTTP em segundos
    """

    def __init__(self, output_dir: str | Path | None = None, timeout: int = 60):
        if output_dir is None:
            from config.settings import settings

            output_dir = settings.data_raw / "cvm"
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "FinancialIntelligencePlatform/1.0 (educational; dados.cvm.gov.br)"}
        )

    # ── API pública ───────────────────────────────────────────────────────────

    def download_dfp(self, year: int, force: bool = False) -> list[Path]:
        """Baixa e extrai os CSVs de DFP para o ano. Pula se já existirem."""
        url = f"{BASE_URL}/DFP/DADOS/dfp_cia_aberta_{year}.zip"
        dest = self.output_dir / "DFP" / str(year)
        return self._download_and_extract(url, dest, label=f"DFP {year}", force=force)

    def download_itr(self, year: int, force: bool = False) -> list[Path]:
        """Baixa e extrai os CSVs de ITR para o ano. Pula se já existirem."""
        url = f"{BASE_URL}/ITR/DADOS/itr_cia_aberta_{year}.zip"
        dest = self.output_dir / "ITR" / str(year)
        return self._download_and_extract(url, dest, label=f"ITR {year}", force=force)

    def download_range(
        self,
        doc_type: DocType,
        start_year: int,
        end_year: int,
        force: bool = False,
    ) -> dict[int, list[Path]]:
        """Baixa múltiplos anos. Respeita rate limit entre requisições."""
        results: dict[int, list[Path]] = {}
        for year in range(start_year, end_year + 1):
            try:
                if doc_type == "DFP":
                    files = self.download_dfp(year, force=force)
                else:
                    files = self.download_itr(year, force=force)
                results[year] = files
                time.sleep(RATE_LIMIT_SECONDS)
            except Exception as exc:
                log.error(f"Falha ao baixar {doc_type} {year}: {exc}")
                results[year] = []
        return results

    def missing_years(
        self,
        doc_type: DocType,
        years: list[int],
    ) -> list[int]:
        """Retorna quais anos ainda não foram baixados localmente."""
        missing = []
        for year in years:
            dest = self.output_dir / doc_type / str(year)
            if not dest.exists() or not list(dest.glob("*.csv")):
                missing.append(year)
        return missing

    def get_local_files(
        self,
        doc_type: DocType,
        year: int,
        dataset: str | None = None,
    ) -> list[Path]:
        """Retorna CSVs já baixados sem nova requisição HTTP."""
        base = self.output_dir / doc_type / str(year)
        if not base.exists():
            return []
        files = list(base.glob("*.csv"))
        if dataset:
            files = [f for f in files if dataset.lower() in f.name.lower()]
        return files

    # ── Internos ─────────────────────────────────────────────────────────────

    def _download_and_extract(
        self,
        url: str,
        dest_dir: Path,
        label: str,
        force: bool = False,
    ) -> list[Path]:
        dest_dir.mkdir(parents=True, exist_ok=True)

        existing = list(dest_dir.glob("*.csv"))
        if existing and not force:
            log.info(f"[{label}] {len(existing)} CSVs já existem — pulando download")
            return existing

        log.info(f"[{label}] Baixando: {url}")
        content = self._fetch(url, label)

        extracted: list[Path] = []
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                out = dest_dir / Path(name).name
                out.write_bytes(zf.read(name))
                extracted.append(out)

        log.info(f"[{label}] {len(extracted)} arquivos extraídos em {dest_dir}")
        return extracted

    @retry(attempts=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _fetch(self, url: str, label: str) -> bytes:
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            raise FileNotFoundError(f"[{label}] Não encontrado na CVM (404): {url}")
        resp.raise_for_status()
        return resp.content


# ── Função de alto nível ──────────────────────────────────────────────────────


def ingest_ticker(
    ticker: str,
    doc_types: list[DocType] | None = None,
    years: list[int] | None = None,
    force: bool = False,
    output_dir: str | Path | None = None,
) -> dict:
    """
    Ingestão incremental para um ticker específico.

    Verifica quais anos ainda não estão locais e baixa apenas o necessário.
    Como os ZIPs da CVM contêm dados de todas as empresas, um download
    beneficia todos os tickers ao mesmo tempo.

    Args:
        ticker: Código de negociação (ex: "BBAS3")
        doc_types: ["DFP"] | ["ITR"] | ["DFP", "ITR"] (default: ambos)
        years: Anos desejados (default: 2019 até ano corrente)
        force: True para re-baixar mesmo se já existir
        output_dir: Override do diretório de saída

    Returns:
        {"ticker": ..., "cvm_code": ..., "downloaded": {DFP: [anos], ITR: [anos]}}
    """
    cvm_code = get_cvm_code(ticker)

    if doc_types is None:
        doc_types = ["DFP", "ITR"]
    if years is None:
        current_year = date.today().year
        years = list(range(2019, current_year + 1))

    dl = CVMDownloader(output_dir=output_dir)
    downloaded: dict[str, list[int]] = {}

    for doc_type in doc_types:
        missing = dl.missing_years(doc_type, years) if not force else years
        if not missing:
            log.info(f"[{ticker}] {doc_type}: todos os anos já disponíveis")
            downloaded[doc_type] = []
            continue

        log.info(f"[{ticker}] {doc_type}: baixando {len(missing)} ano(s): {missing}")
        downloaded[doc_type] = []
        for year in missing:
            try:
                if doc_type == "DFP":
                    files = dl.download_dfp(year, force=force)
                else:
                    files = dl.download_itr(year, force=force)
                if files:
                    downloaded[doc_type].append(year)
                time.sleep(RATE_LIMIT_SECONDS)
            except Exception as exc:
                log.error(f"[{ticker}] {doc_type} {year}: {exc}")

    log.success(f"[{ticker}] Ingestão CVM concluída — CVM code: {cvm_code}")
    return {"ticker": ticker, "cvm_code": cvm_code, "downloaded": downloaded}
