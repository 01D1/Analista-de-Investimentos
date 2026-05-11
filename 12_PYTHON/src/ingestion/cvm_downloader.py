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
import sqlite3
import time
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import pdfplumber
import requests
import yaml

from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)

BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
RATE_LIMIT_SECONDS = 1.5
DocType = Literal["DFP", "ITR"]

# ── IPE event classification ──────────────────────────────────────────────────

IPE_EVENT_TYPE_MAP: dict[str, str] = {
    "Resultados": "earnings",
    "Fato Relevante": "material_fact",
    "Assembleia": "meeting",
    "Comunicado ao Mercado": "announcement",
    "Aviso aos Acionistas": "shareholder_notice",
    "Distribuição de Proventos": "dividend",
    "Acordo de Acionistas": "shareholder_agreement",
}


def classify_event(categoria: str) -> str:
    """Map IPE Categoria column to internal event_type string."""
    return IPE_EVENT_TYPE_MAP.get(categoria.strip(), "other")


def extract_ipe_pdf_text(pdf_url: str) -> str:
    """Download IPE PDF from Link_Download and extract text with pdfplumber.

    Returns empty string on any failure — never blocks ingestion.
    Caps extraction at 10 pages to mitigate T-02-03 (DoS via large PDFs).
    """
    try:
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages[:10]
            )
    except Exception as exc:
        log.warning(f"[ipe_pdf] extração falhou: {exc}")
        return ""


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

    def get_cvm_code(self, ticker: str) -> str:
        """Retorna o CD_CVM de um ticker (6 dígitos, zero-padded). Delega ao módulo."""
        return get_cvm_code(ticker)

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

    def download_ipe(self, year: int, force: bool = False) -> list[Path]:
        """Baixa e extrai o CSV de IPE para o ano. Pula se já existir."""
        url = f"{BASE_URL}/IPE/DADOS/ipe_cia_aberta_{year}.zip"
        dest = self.output_dir / "IPE" / str(year)
        time.sleep(RATE_LIMIT_SECONDS)
        return self._download_and_extract(url, dest, label=f"IPE {year}", force=force)

    def write_to_db(
        self,
        records: list[dict],
        conn: sqlite3.Connection,
    ) -> int:
        """Insert CVM records into cvm_statements. Returns count of new rows inserted.

        Uses INSERT OR IGNORE — duplicate (ticker, period_type, year, account_code,
        reference_date) rows are silently skipped (T-02-01: parameterized queries only).
        """
        inserted = 0
        now = datetime.utcnow().isoformat()
        for rec in records:
            cur = conn.execute(
                """INSERT OR IGNORE INTO cvm_statements
                   (id, ticker, cvm_code, year, period_type, account_code,
                    account_name, normalized_name, value, reference_date, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    rec["ticker"],
                    rec["cvm_code"],
                    rec["year"],
                    rec["period_type"],
                    rec.get("account_code"),
                    rec.get("account_name"),
                    rec.get("normalized_name"),
                    rec.get("value"),
                    rec.get("reference_date"),
                    now,
                ),
            )
            inserted += cur.rowcount  # 1 on insert, 0 on OR IGNORE — reliable
        conn.commit()  # single commit after all rows
        return inserted

    def parse_and_store(
        self,
        ticker: str,
        year: int,
        period_type: str,
        conn: sqlite3.Connection,
        raw_dir: Path,
    ) -> int:
        """Download CVM ZIP, filter to ticker, save raw CSV, parse, write to DB.

        Args:
            ticker: B3 ticker code (e.g. "BBAS3")
            year: Calendar year to download
            period_type: "DFP" or "ITR"
            conn: Open sqlite3 connection to ingestion.db
            raw_dir: Base directory for raw CSVs (settings.data_raw / "cvm")

        Returns:
            Count of rows inserted into cvm_statements.
        """
        import pandas as pd

        cvm_code = self.get_cvm_code(ticker)

        if period_type == "DFP":
            csv_paths = self.download_dfp(year)
        else:
            csv_paths = self.download_itr(year)

        records: list[dict] = []
        for csv_path in csv_paths:
            df = pd.read_csv(csv_path, encoding="iso-8859-1", sep=";", dtype=str)
            df["CD_CVM"] = df["CD_CVM"].astype(str).str.strip().str.zfill(6)
            filtered = df[df["CD_CVM"] == cvm_code].copy()
            if filtered.empty:
                continue

            # D-09: Save raw filtered CSV before any processing
            raw_out = raw_dir / str(year) / f"{ticker}_{period_type}_{csv_path.stem}.csv"
            raw_out.parent.mkdir(parents=True, exist_ok=True)
            filtered.to_csv(raw_out, index=False, encoding="utf-8")

            # ING-02: ITR reconciliation — keep only ÚLTIMO for overlapping periods
            if period_type == "ITR" and "ORDEM_EXERC" in filtered.columns:
                filtered = filtered[filtered["ORDEM_EXERC"].str.strip() == "\xda\x4c\x54\x49\x4d\x4f"]

            for _, row in filtered.iterrows():
                scale = {"MIL": 1_000, "UNIDADE": 1}.get(
                    str(row.get("ESCALA_MOEDA", "UNIDADE")).strip(), 1
                )
                try:
                    value = float(str(row.get("VL_CONTA", "")).replace(",", ".")) * scale
                except (ValueError, TypeError):
                    value = None
                account_code = str(row.get("CD_CONTA", "")).strip()
                account_name = str(row.get("DS_CONTA", "")).strip()
                records.append({
                    "ticker": ticker,
                    "cvm_code": cvm_code,
                    "year": year,
                    "period_type": period_type,
                    "account_code": account_code,
                    "account_name": account_name,
                    "normalized_name": None,  # Phase 3 enrichment
                    "value": value,
                    "reference_date": str(row.get("DT_FIM_EXERC", "")).strip() or None,
                })

        return self.write_to_db(records, conn)

    def parse_and_store_ipe(
        self,
        ticker: str,
        year: int,
        conn: sqlite3.Connection,
        extract_pdf: bool = True,
    ) -> int:
        """Download IPE CSV, filter to ticker, classify events, extract PDF text, write to DB.

        Args:
            ticker: B3 ticker code
            year: Calendar year
            conn: Open sqlite3 connection to ingestion.db
            extract_pdf: Set False to skip PDF download (useful for tests / dry runs)

        Returns:
            Count of rows inserted.
        """
        import pandas as pd

        cvm_code = self.get_cvm_code(ticker)
        csv_paths = self.download_ipe(year)

        records: list[dict] = []
        for csv_path in csv_paths:
            df = pd.read_csv(csv_path, encoding="iso-8859-1", sep=";", dtype=str)
            df["Codigo_CVM"] = df["Codigo_CVM"].astype(str).str.strip().str.zfill(6)
            filtered = df[df["Codigo_CVM"] == cvm_code].copy()
            if filtered.empty:
                continue

            for _, row in filtered.iterrows():
                categoria = str(row.get("Categoria", "")).strip()
                event_type = classify_event(categoria)
                pdf_text = ""
                link = str(row.get("Link_Download", "")).strip()
                if extract_pdf and link.startswith("http"):
                    pdf_text = extract_ipe_pdf_text(link)

                records.append({
                    "ticker": ticker,
                    "cvm_code": cvm_code,
                    "year": year,
                    "period_type": "IPE",
                    "account_code": event_type,
                    "account_name": pdf_text[:4000] if pdf_text else categoria,
                    "normalized_name": categoria,
                    "value": None,
                    "reference_date": str(row.get("Data_Referencia", "")).strip() or None,
                })

        return self.write_to_db(records, conn)

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
