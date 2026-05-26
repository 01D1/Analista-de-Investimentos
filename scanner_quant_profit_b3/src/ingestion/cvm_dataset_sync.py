"""
cvm_dataset_sync.py
--------------------
M017-S02.5 — CVM Full Dataset Localizer / Downloader

Varre todos os ZIPs CVM já baixados localmente (DFP 2019-2026, ITR 2019-2026),
filtra as linhas de cada ticker mapeado em cvm_codes.yaml, salva CSVs filtrados
por ticker em data/raw/cvm/filtered/ e produz um JSON de cobertura usado para
gerar docs/M017_S02.5_DATASET_AUDIT.md.

Exclusões explícitas:
  - PETZ3: LEGACY_TICKER — extinto por corporate action (fusão com Cobasi → AUAU3)
  - AUAU3: CVM code null — CNPJ ainda não mapeado

Statement types cobertos (CON + IND):
  BPA, BPP, DRE, DFC_MD, DFC_MI, DVA, DMPL

Uso:
    cd 12_PYTHON
    python -m src.ingestion.cvm_dataset_sync          # relatório completo
    python -m src.ingestion.cvm_dataset_sync --dry-run # apenas contagem, sem salvar CSVs
    python -m src.ingestion.cvm_dataset_sync --years 2024,2025   # anos específicos
    python -m src.ingestion.cvm_dataset_sync --tickers BBAS3,ITUB4  # tickers específicos

Saídas:
    data/raw/cvm/filtered/{TICKER}/{DOC}_{YEAR}_{STMT}.csv
    data/raw/cvm/coverage_audit.json
    docs/M017_S02.5_DATASET_AUDIT.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent   # 12_PYTHON/
CVM_RAW = ROOT / "data" / "raw" / "cvm"
FILTERED_BASE = CVM_RAW / "filtered"
COVERAGE_JSON = CVM_RAW / "coverage_audit.json"
AUDIT_MD = ROOT / "docs" / "M017_S02.5_DATASET_AUDIT.md"

# ── Constantes ────────────────────────────────────────────────────────────────

YEARS = list(range(2019, 2026))     # 2019..2025 inclusive (anos completos)
YEARS_PARTIAL = [2026]              # 2026 = dados parciais — processado separadamente
YEARS_ALL = YEARS + YEARS_PARTIAL   # usado quando --include-2026 é passado

# Statement types que nos interessam (CON = consolidado, IND = individual)
STMT_TYPES = [
    "BPA_con", "BPA_ind",
    "BPP_con", "BPP_ind",
    "DRE_con", "DRE_ind",
    "DFC_MD_con", "DFC_MD_ind",
    "DFC_MI_con", "DFC_MI_ind",
    "DVA_con", "DVA_ind",
    "DMPL_con", "DMPL_ind",
]

DOC_TYPES = ["DFP", "ITR"]

# Tickers excluídos explicitamente (condição de execução)
EXCLUDED = {"PETZ3", "AUAU3"}

# Tickers com mesmo CVM code que outro ticker (share de CD_CVM)
# Os dados são idênticos — filtragem acontece pelo CD_CVM
CODEDUP_TICKERS = {
    "BBDC3": "BBDC4",    # mesmo CNPJ → 000906
    "PETR3": "PETR4",    # mesmo CNPJ → 009512
    "AXIA6": "AXIA3",    # mesmo CNPJ → 002437
}

# 18 NEEDS_FINANCIALS — tickers prioritários para validação
# Critério: dados incompletos (< 7 anos DFP/ITR), IPO recente,
# reestruturação corporativa significativa ou relevância alta
NEEDS_FINANCIALS_18 = [
    # Gaps severos de cobertura CVM
    "EQTL3",   # CVM code 027553 só válido a partir de 2023 (nova holding pós-privatização Eletrobras)
    "AMOB3",   # IPO 2023 — dados apenas de 2023+
    "VAMO3",   # IPO 2020 — histórico parcial
    "AURE3",   # IPO 2021 — histórico parcial
    "RECV3",   # IPO 2020 — histórico parcial
    "INTR4",   # Inter & Co: listagem B3 como INTR4 em 2021, estrutura BDR
    # Reestruturações corporativas (validação necessária)
    "BRAV3",   # 3R Petroleum + HRT → Brava Energia (2024) — gap histórico esperado
    "CMIN3",   # Spinoff CSN Mineração (IPO 2021) — dados pré-spinoff misturados
    "AXIA3",   # Privatização Eletrobras → Axia Energia (2023) — CD_CVM herdado
    "RAIZ4",   # Raizen: IPO 2021, estrutura holding joint-venture Shell + Cosan
    # Alta relevância + eventos corporativos
    "RDOR3",   # IPO 2021 — Rede D'Or
    "HAPV3",   # IPO 2021 + M&A Hapvida-Notre Dame (fusão 2022)
    "SMTO3",   # Exercício fiscal março (não dezembro) — requer ajuste de período
    "CRFB3",   # Atacadão listado como Carrefour Brasil (2022) — histórico parcial
    "ALOS3",   # Allos = fusão Aliansce + BR Malls (2022) — dados pré-fusão misto
    "IGTI11",  # Iguatemi: reestruturação e mudança de nome 2022
    "COGN3",   # Estresse financeiro + reestruturação (Kroton)
    "AZUL4",   # Estresse financeiro + plano de recuperação 2024
]

CHUNKSIZE = 50_000   # linhas por chunk — evita OOM em CSVs de 6MB+

# ── Helpers ───────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_cvm_codes(exclude: set[str] | None = None) -> dict[str, str]:
    """Carrega cvm_codes.yaml → {ticker: cvm_code (6-digits zero-padded)}.

    Exclui tickers em `exclude` e tickers com cvm_code null.
    """
    cfg_path = ROOT / "config" / "cvm_codes.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    codes: dict[str, str] = {}
    for ticker, code in data.get("cvm_codes", {}).items():
        if exclude and ticker in exclude:
            continue
        if code is None:
            continue
        codes[ticker] = str(code).zfill(6)
    return codes


def build_reverse_map(codes: dict[str, str]) -> dict[str, list[str]]:
    """CD_CVM → [tickers] — múltiplos tickers podem ter o mesmo código."""
    rev: dict[str, list[str]] = defaultdict(list)
    for ticker, cvm_code in codes.items():
        rev[cvm_code].append(ticker)
    return dict(rev)


def csv_path(doc_type: str, year: int, stmt: str) -> Path:
    """Retorna o Path canônico do CSV para um dado doc_type/year/stmt."""
    prefix = doc_type.lower()  # dfp | itr
    return CVM_RAW / doc_type / str(year) / f"{prefix}_cia_aberta_{stmt}_{year}.csv"


class CoverageRecord(NamedTuple):
    ticker: str
    cvm_code: str
    doc_type: str
    year: int
    stmt_type: str
    csv_exists: bool
    row_count: int
    has_data: bool


# ── Core: scan + filter ───────────────────────────────────────────────────────

def scan_year_stmt(
    doc_type: str,
    year: int,
    stmt: str,
    rev_map: dict[str, list[str]],
    dry_run: bool = False,
) -> tuple[list[CoverageRecord], dict[str, pd.DataFrame]]:
    """Lê um CSV CVM, filtra todos os tickers em rev_map, retorna cobertura + dataframes.

    Nunca carrega o CSV inteiro de uma vez — usa chunksize=50_000.
    Retorna (coverage_records, {ticker: filtered_df}).
    """
    path = csv_path(doc_type, year, stmt)
    all_codes = set(rev_map.keys())

    if not path.exists():
        # CSV não baixado — registrar ausência para todos os tickers
        records = []
        for cvm_code, tickers in rev_map.items():
            for ticker in tickers:
                records.append(CoverageRecord(
                    ticker=ticker,
                    cvm_code=cvm_code,
                    doc_type=doc_type,
                    year=year,
                    stmt_type=stmt,
                    csv_exists=False,
                    row_count=0,
                    has_data=False,
                ))
        return records, {}

    # Acumula por CD_CVM para eficiência
    chunks_by_code: dict[str, list[pd.DataFrame]] = defaultdict(list)
    total_rows = 0

    try:
        for chunk in pd.read_csv(
            path,
            encoding="iso-8859-1",
            sep=";",
            dtype=str,
            chunksize=CHUNKSIZE,
        ):
            if "CD_CVM" not in chunk.columns:
                break
            chunk["CD_CVM"] = chunk["CD_CVM"].astype(str).str.strip().str.zfill(6)
            filtered = chunk[chunk["CD_CVM"].isin(all_codes)]
            if filtered.empty:
                continue
            total_rows += len(filtered)
            for cvm_code, group in filtered.groupby("CD_CVM"):
                chunks_by_code[cvm_code].append(group)
    except Exception as exc:
        _log(f"  ERRO lendo {path.name}: {exc}")
        # Retorna cobertura marcada como erro mas csv_exists=True
        records = []
        for cvm_code, tickers in rev_map.items():
            for ticker in tickers:
                records.append(CoverageRecord(
                    ticker=ticker,
                    cvm_code=cvm_code,
                    doc_type=doc_type,
                    year=year,
                    stmt_type=stmt,
                    csv_exists=True,
                    row_count=-1,   # sinaliza erro de leitura
                    has_data=False,
                ))
        return records, {}

    # Consolida DataFrames por código e converte para ticker(s)
    ticker_dfs: dict[str, pd.DataFrame] = {}
    records: list[CoverageRecord] = []

    for cvm_code, tickers in rev_map.items():
        df_parts = chunks_by_code.get(cvm_code, [])
        if df_parts:
            df = pd.concat(df_parts, ignore_index=True)
            row_count = len(df)
            has_data = row_count > 0
        else:
            df = pd.DataFrame()
            row_count = 0
            has_data = False

        for ticker in tickers:
            records.append(CoverageRecord(
                ticker=ticker,
                cvm_code=cvm_code,
                doc_type=doc_type,
                year=year,
                stmt_type=stmt,
                csv_exists=True,
                row_count=row_count,
                has_data=has_data,
            ))
            if has_data and not dry_run:
                ticker_dfs[ticker] = df  # compartilha o mesmo df para tickers duplicados

    return records, ticker_dfs


def save_filtered_csv(
    ticker: str,
    doc_type: str,
    year: int,
    stmt: str,
    df: pd.DataFrame,
) -> Path:
    """Salva CSV filtrado por ticker. Retorna o Path gravado."""
    out_dir = FILTERED_BASE / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{doc_type}_{year}_{stmt}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    return out_path


# ── Orquestrador ──────────────────────────────────────────────────────────────

def run_sync(
    years: list[int] | None = None,
    tickers_filter: set[str] | None = None,
    dry_run: bool = False,
) -> list[CoverageRecord]:
    """Executa o scan completo e salva CSVs filtrados.

    Args:
        years: Subset de anos (default: YEARS = 2019-2026)
        tickers_filter: Se fornecido, processa apenas esses tickers
        dry_run: Se True, não salva CSVs filtrados

    Returns:
        Lista completa de CoverageRecord para todos tickers × anos × stmt_types
    """
    _log("Iniciando M017-S02.5 CVM Dataset Sync")
    _log(f"  dry_run={dry_run}")

    # Carrega mapa de códigos
    codes = load_cvm_codes(exclude=EXCLUDED)
    if tickers_filter:
        codes = {t: c for t, c in codes.items() if t in tickers_filter}
    rev_map = build_reverse_map(codes)

    _log(f"  Tickers a processar: {len(codes)} | CVM codes únicos: {len(rev_map)}")
    _log(f"  Anos: {years or YEARS}")

    target_years = years if years is not None else YEARS
    all_records: list[CoverageRecord] = []
    total_csvs_saved = 0
    t0 = time.monotonic()

    for doc_type in DOC_TYPES:
        for year in target_years:
            _log(f"  [{doc_type}] {year} — varrendo {len(STMT_TYPES)} statement types...")
            year_saved = 0
            year_rows = 0

            for stmt in STMT_TYPES:
                records, ticker_dfs = scan_year_stmt(doc_type, year, stmt, rev_map, dry_run)
                all_records.extend(records)

                rows_this_stmt = sum(r.row_count for r in records if r.row_count > 0)
                year_rows += rows_this_stmt

                if not dry_run:
                    for ticker, df in ticker_dfs.items():
                        save_filtered_csv(ticker, doc_type, year, stmt, df)
                        year_saved += 1

                total_csvs_saved += year_saved

            found_tickers = sum(1 for r in all_records if r.doc_type == doc_type and r.year == year and r.has_data)
            _log(f"    → {year_rows:,} linhas | {year_saved} CSVs salvos | {found_tickers} tickers com dados")

    elapsed = time.monotonic() - t0
    _log(f"Sync concluído em {elapsed:.1f}s — {len(all_records)} registros | {total_csvs_saved} CSVs salvos")
    return all_records


# ── Coverage report ───────────────────────────────────────────────────────────

def build_coverage_json(records: list[CoverageRecord], codes: dict[str, str]) -> dict:
    """Constrói dict de cobertura para serialização JSON."""
    # Agrupa por ticker
    by_ticker: dict[str, dict] = {}
    for r in records:
        if r.ticker not in by_ticker:
            by_ticker[r.ticker] = {
                "cvm_code": r.cvm_code,
                "codedup_of": CODEDUP_TICKERS.get(r.ticker),
                "is_needs_financials": r.ticker in NEEDS_FINANCIALS_18,
                "total_rows": 0,
                "stmt_coverage": {},       # {stmt_type: {year: row_count}}
                "years_with_data": set(),
                "gaps": [],
                "doc_type_summary": {},    # {doc_type: {year: row_count}}
            }
        entry = by_ticker[r.ticker]
        entry["total_rows"] += max(r.row_count, 0)

        if r.csv_exists and r.row_count > 0:
            entry["years_with_data"].add(r.year)

        stmt_key = r.stmt_type
        if stmt_key not in entry["stmt_coverage"]:
            entry["stmt_coverage"][stmt_key] = {}
        entry["stmt_coverage"][stmt_key][r.year] = r.row_count

        doc_key = r.doc_type
        if doc_key not in entry["doc_type_summary"]:
            entry["doc_type_summary"][doc_key] = {}
        if r.year not in entry["doc_type_summary"][doc_key]:
            entry["doc_type_summary"][doc_key][r.year] = 0
        entry["doc_type_summary"][doc_key][r.year] += max(r.row_count, 0)

    # Identifica gaps e converte sets
    for ticker, entry in by_ticker.items():
        entry["years_with_data"] = sorted(entry["years_with_data"])
        all_expected_years = [y for y in YEARS if y <= 2025]  # 2026 parcial → não conta como gap
        gaps = [y for y in all_expected_years if y not in entry["years_with_data"]]
        entry["gaps"] = gaps

    # Sumário global
    tickers_complete = sum(1 for e in by_ticker.values() if not e["gaps"])
    tickers_partial = sum(1 for e in by_ticker.values() if e["gaps"] and e["total_rows"] > 0)
    tickers_missing = sum(1 for e in by_ticker.values() if e["total_rows"] == 0)

    nf_coverage = {t: by_ticker.get(t, {}) for t in NEEDS_FINANCIALS_18}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tickers": len(by_ticker),
        "years_scanned": YEARS,
        "stmt_types": STMT_TYPES,
        "summary": {
            "complete": tickers_complete,
            "partial": tickers_partial,
            "missing": tickers_missing,
        },
        "tickers": by_ticker,
        "needs_financials_18": nf_coverage,
    }


# ── Markdown report ───────────────────────────────────────────────────────────

def _status_icon(entry: dict) -> str:
    if entry["total_rows"] == 0:
        return "❌"
    if entry["gaps"]:
        return "⚠️"
    return "✅"


def generate_audit_md(coverage: dict) -> str:
    """Gera o conteúdo Markdown do relatório de auditoria."""
    ts = coverage["generated_at"]
    summary = coverage["summary"]
    tickers = coverage["tickers"]

    lines: list[str] = []
    lines.append("# M017-S02.5 — CVM Full Dataset Audit")
    lines.append("")
    lines.append(f"> Gerado em: {ts}")
    lines.append(f"> Anos varridos: {coverage['years_scanned'][0]}–{coverage['years_scanned'][-1]}")
    lines.append(f"> Statement types: {len(coverage['stmt_types'])} (BPA/BPP/DRE/DFC/DVA/DMPL × CON/IND)")
    lines.append(f"> Tickers processados: {coverage['total_tickers']}")
    lines.append(f"> Exclusões: PETZ3 (LEGACY), AUAU3 (CNPJ null)")
    lines.append("")

    # ── 1. Sumário executivo ──────────────────────────────────────────────────
    lines.append("## 1. Sumário Executivo")
    lines.append("")
    lines.append("| Status | Tickers | Significado |")
    lines.append("|--------|--------:|-------------|")
    lines.append(f"| ✅ Cobertura completa | {summary['complete']} | Dados em todos os anos 2019–2025 |")
    lines.append(f"| ⚠️ Cobertura parcial | {summary['partial']} | Dados em alguns anos (gaps esperados: IPO recente, reestruturação) |")
    lines.append(f"| ❌ Sem dados | {summary['missing']} | Nenhuma linha encontrada |")
    lines.append("")

    # Fonte local confirmada
    lines.append("### Fontes locais confirmadas")
    lines.append("")
    lines.append("| Doc Type | Anos Disponíveis | Observação |")
    lines.append("|----------|-----------------|------------|")
    lines.append("| DFP | 2019–2025 (completo) + 2026 (parcial) | ~240–293 MB por ano |")
    lines.append("| ITR | 2019–2025 (completo) + 2026 (mínimo) | ~625–834 MB por ano |")
    lines.append("")
    lines.append("> **2026**: DFP 2026 contém empresas que publicaram o FY2025 até mai/2026 (~25-44KB por stmt). ")
    lines.append("> ITR 2026 contém apenas Q1 2026 de poucas empresas (440KB total). Não tratado como gap.")
    lines.append("")

    # ── 2. 18 NEEDS_FINANCIALS ───────────────────────────────────────────────
    lines.append("## 2. Subseção Prioritária — 18 NEEDS_FINANCIALS")
    lines.append("")
    lines.append("Tickers identificados para validação prioritária de inputs financeiros.")
    lines.append("Critério: gaps de cobertura CVM, IPO recente, reestruturação corporativa ou alta relevância.")
    lines.append("")
    lines.append("| # | Ticker | CVM Code | Anos com Dados | Gaps (2019-2025) | Total Linhas | Motivo |")
    lines.append("|---|--------|----------|---------------|-----------------|-------------|--------|")

    nf_reasons = {
        "EQTL3": "CD_CVM 027553 só válido a partir de 2023 (nova holding pós-privatização Eletrobras)",
        "AMOB3": "IPO 2023 — histórico CVM inexistente antes da listagem",
        "VAMO3": "IPO 2020 — histórico parcial (5 anos vs 7 esperados)",
        "AURE3": "IPO 2021 — histórico parcial (5 anos)",
        "RECV3": "IPO 2020 — histórico parcial (6 anos)",
        "INTR4": "Inter & Co: listou como INTR4 em 2021 (BDR), estrutura não-convencional",
        "BRAV3": "3R Petroleum + HRT → Brava Energia (2024) — gap histórico na consolidação",
        "CMIN3": "Spinoff CSN Mineração (IPO 2021) — dados pré-spinoff misturados com CSNA3",
        "AXIA3": "Privatização Eletrobras → Axia Energia (2023) — CD_CVM herdado, validar continuidade",
        "RAIZ4": "Raizen: IPO 2021, holding joint-venture Shell + Cosan com exercício fiscal diferente",
        "RDOR3": "IPO 2021 — Rede D'Or",
        "HAPV3": "IPO 2021 + M&A Hapvida-Notre Dame (fusão 2022) — demonstrações pro-forma",
        "SMTO3": "Exercício fiscal encerra em março (não dezembro) — requer ajuste de período no valuation",
        "CRFB3": "Atacadão listado como entidade standalone desde 2022 — histórico curto na CVM",
        "ALOS3": "Fusão Aliansce + BR Malls (2022) — dados pré-fusão de entidades distintas",
        "IGTI11": "Iguatemi: reestruturação e renomeação 2022",
        "COGN3": "Estresse financeiro + reestruturação (ex-Kroton Educacional)",
        "AZUL4": "Estresse financeiro + plano de recuperação 2024 — valiation inputs críticos",
    }

    for i, ticker in enumerate(NEEDS_FINANCIALS_18, 1):
        entry = tickers.get(ticker, {})
        cvm_code = entry.get("cvm_code", "N/A")
        years_with_data = entry.get("years_with_data", [])
        gaps = entry.get("gaps", [])
        total_rows = entry.get("total_rows", 0)
        reason = nf_reasons.get(ticker, "")
        years_str = f"{min(years_with_data)}–{max(years_with_data)}" if years_with_data else "—"
        gaps_str = ", ".join(str(g) for g in gaps) if gaps else "Nenhum"
        status = _status_icon(entry) if entry else "❓"
        lines.append(
            f"| {i} | {status} **{ticker}** | {cvm_code} | {years_str} | {gaps_str} | {total_rows:,} | {reason} |"
        )

    lines.append("")

    # ── 3. Inventário completo por ticker ─────────────────────────────────────
    lines.append("## 3. Inventário Completo — Todos os Tickers")
    lines.append("")
    lines.append("Formato: ✅ cobertura completa 2019-2025 | ⚠️ gaps | ❌ sem dados")
    lines.append("")

    # Agrupa por setor/tipo baseado no YAML (usa prefixo do ticker como proxy)
    # Simplesmente lista em ordem alfabética por setor com base nos grupos do YAML
    sector_groups = {
        "Bancos / Financeiros": ["BBAS3","ITUB4","BBDC4","BBDC3","SANB11","BPAC11","BRSR6","ABCB4","BMGB4","BPAN4","PINE4","INTR4"],
        "Holdings Financeiras": ["ITSA4","BBSE3","BRAP4","IRBR3","PSSA3","CXSE3","B3SA3"],
        "Petróleo & Gás": ["PETR4","PETR3","PRIO3","BRAV3","RECV3","VBBR3","RAIZ4","ENEV3","CSAN3"],
        "Mineração / Siderurgia": ["VALE3","CMIN3","GGBR4","GOAU4","CSNA3","USIM5","BRKM5"],
        "Utilities / Energia Elétrica": ["AXIA3","AXIA6","CMIG4","CPFE3","CPLE6","EGIE3","ENGI11","EQTL3","AURE3","ISAE4","TAEE11","SBSP3"],
        "Telecom": ["VIVT3","TIMS3"],
        "Industrial / Conglomerados": ["WEGE3","EMBR3","POMO4","STBP3","CCRO3","RAIL3","UGPA3"],
        "Papel & Celulose": ["SUZB3","KLBN11"],
        "Alimentos & Bebidas": ["ABEV3","JBSS3","BRFS3","MRFG3","BEEF3","SMTO3","SLCE3"],
        "Varejo": ["LREN3","MGLU3","AZZA3","NTCO3","CRFB3","PCAR3","VIVA3","AMOB3"],
        "Saúde": ["RDOR3","HAPV3","FLRY3","HYPE3","RADL3"],
        "Real Estate / Shopping": ["MULT3","CYRE3","MRVE3","IGTI11","ALOS3"],
        "Locação / Serviços": ["RENT3","VAMO3"],
        "Tecnologia": ["TOTS3","LWSA3"],
        "Educação": ["COGN3","YDUQ3"],
        "Aviação": ["AZUL4"],
        "Outros": ["CVCB3"],
    }

    for sector, sector_tickers in sector_groups.items():
        lines.append(f"### {sector}")
        lines.append("")
        lines.append("| Ticker | CVM Code | Anos com Dados | Gaps | Total Linhas (DFP+ITR) | Code-Dup |")
        lines.append("|--------|----------|---------------|------|----------------------|---------|")
        for ticker in sector_tickers:
            entry = tickers.get(ticker, {})
            if not entry:
                # Ticker excluído ou não processado
                lines.append(f"| {ticker} | — | — | — | — | — |")
                continue
            cvm_code = entry.get("cvm_code", "N/A")
            years_data = entry.get("years_with_data", [])
            gaps = entry.get("gaps", [])
            total_rows = entry.get("total_rows", 0)
            codedup = entry.get("codedup_of") or ""
            status = _status_icon(entry)
            years_str = f"{min(years_data)}–{max(years_data)}" if years_data else "—"
            gaps_str = ", ".join(str(g) for g in gaps) if gaps else "—"
            nf_mark = " ⭐" if ticker in NEEDS_FINANCIALS_18 else ""
            lines.append(
                f"| {status} **{ticker}**{nf_mark} | {cvm_code} | {years_str} | {gaps_str} | {total_rows:,} | {codedup} |"
            )
        lines.append("")

    # ── 4. Ausências, falhas e pendências ──────────────────────────────────────
    lines.append("## 4. Ausências, Falhas e Pendências")
    lines.append("")

    # 4.1 Tickers sem dados
    no_data = [t for t, e in tickers.items() if e.get("total_rows", 0) == 0]
    lines.append("### 4.1 Tickers sem nenhuma linha encontrada nos CSVs")
    lines.append("")
    if no_data:
        for t in sorted(no_data):
            cvm_code = tickers[t].get("cvm_code", "N/A")
            lines.append(f"- **{t}** (CD_CVM: {cvm_code})")
    else:
        lines.append("_Nenhum ticker com zero linhas._")
    lines.append("")

    # 4.2 Tickers com gaps em anos esperados
    lines.append("### 4.2 Tickers com gaps em 2019–2025")
    lines.append("")
    lines.append("| Ticker | Anos Faltando | Possível Causa |")
    lines.append("|--------|--------------|----------------|")

    gap_causes = {
        "EQTL3": "CD_CVM 027553 atribuído somente em 2023",
        "AMOB3": "IPO 2023",
        "VAMO3": "IPO 2020",
        "AURE3": "IPO 2021",
        "RECV3": "IPO 2020",
        "INTR4": "Listagem INTR4 em 2021",
        "BRAV3": "Reestruturação 3R→Brava 2024",
        "CMIN3": "IPO CSN Mineração 2021",
        "RAIZ4": "IPO 2021",
        "RDOR3": "IPO 2021",
        "HAPV3": "IPO 2021",
        "CRFB3": "Listagem Atacadão standalone 2022",
        "PETZ3": "LEGACY — excluído",
    }

    partial_tickers = [(t, e) for t, e in tickers.items() if e.get("gaps") and e.get("total_rows", 0) > 0]
    partial_tickers.sort(key=lambda x: (len(x[1].get("gaps", [])), x[0]), reverse=True)

    for ticker, entry in partial_tickers:
        gaps = entry.get("gaps", [])
        gaps_str = ", ".join(str(g) for g in gaps)
        cause = gap_causes.get(ticker, "Verificar histórico CVM")
        lines.append(f"| **{ticker}** | {gaps_str} | {cause} |")

    lines.append("")

    # 4.3 Stmt types com cobertura limitada
    lines.append("### 4.3 Observações sobre Statement Types")
    lines.append("")
    lines.append("| Statement | Situação |")
    lines.append("|-----------|---------|")
    lines.append("| DFC_MD (Método Direto) | Disponível mas menos utilizado pelas empresas brasileiras (maioria usa DFC_MI) |")
    lines.append("| DFC_MI (Método Indireto) | Padrão de mercado — cobertura alta |")
    lines.append("| DMPL | Mutações do PL — nem todas as empresas publicam separadamente |")
    lines.append("| DVA | Valor Adicionado — publicado na maioria dos DFPs, menos nas ITRs |")
    lines.append("| DRA | *Não incluído no escopo deste audit* (Resultado Abrangente) |")
    lines.append("")

    # 4.4 DFP 2026 e ITR 2026
    lines.append("### 4.4 Status de 2026")
    lines.append("")
    lines.append("| Documento | Status | Detalhe |")
    lines.append("|-----------|--------|---------|")
    lines.append("| DFP 2026 | ⚠️ Parcial | Arquivos existem mas muito menores (~25-44KB vs ~6MB do 2024). Apenas empresas que entregaram o FY2025 até mai/2026. |")
    lines.append("| ITR 2026 | ⚠️ Mínimo | 440KB total — possivelmente apenas Q4 2025 ou Q1 2026 de poucos emissores. |")
    lines.append("")
    lines.append("> Ação recomendada: Re-executar `cvm_dataset_sync.py` em agosto/2026 após encerramento da janela de entrega do FY2025.")
    lines.append("")

    # ── 5. Próximos passos ────────────────────────────────────────────────────
    lines.append("## 5. Próximos Passos (Pós-Revisão)")
    lines.append("")
    lines.append("1. **Revisão manual** dos 18 NEEDS_FINANCIALS — validar se os gaps são esperados ou erros")
    lines.append("2. **M017-S03** — Extração de métricas financeiras dos CSVs filtrados → `valuation_financial_inputs`")
    lines.append("   - Prioridade: DFP 2019–2025 (anual, CON preferencial)")
    lines.append("   - Bancos: usar DRE_con para NIM/ROE; BPA_con para total assets")
    lines.append("   - Não-bancos: DRE_con para EBITDA; BPA_con + BPP_con para leverage")
    lines.append("3. **EQTL3**: verificar se existe CD_CVM legado (ex-Equatorial Energia pré-2023) — pode ser 010430")
    lines.append("4. **SMTO3**: documentar ajuste de período (exercício fiscal de abril a março)")
    lines.append("5. **Tickers code-dup** (BBDC3/BBDC4, PETR3/PETR4, AXIA3/AXIA6): confirmar que basta ingerir")
    lines.append("   um dos dois (já que CD_CVM é idêntico)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Relatório gerado automaticamente por `src/ingestion/cvm_dataset_sync.py` em {ts}*")

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="M017-S02.5 — CVM Dataset Sync & Audit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas escaneia e conta — não salva CSVs filtrados",
    )
    parser.add_argument(
        "--years",
        type=str,
        default=None,
        help="Anos separados por vírgula (ex: 2024,2025). Default: 2019-2026",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Tickers separados por vírgula (ex: BBAS3,ITUB4). Default: todos",
    )
    parser.add_argument(
        "--no-md",
        action="store_true",
        help="Não gera o Markdown de auditoria",
    )
    parser.add_argument(
        "--include-2026",
        action="store_true",
        help="Inclui 2026 no scan (dados parciais — pode causar timeout em OneDrive)",
    )
    args = parser.parse_args(argv)

    target_years: list[int] | None = None
    if args.years:
        target_years = [int(y.strip()) for y in args.years.split(",")]
    elif getattr(args, "include_2026", False):
        target_years = YEARS_ALL

    tickers_filter: set[str] | None = None
    if args.tickers:
        tickers_filter = {t.strip().upper() for t in args.tickers.split(",")}

    # Executa o sync
    records = run_sync(
        years=target_years,
        tickers_filter=tickers_filter,
        dry_run=args.dry_run,
    )

    # Carrega mapa completo para o relatório (pode diferir do tickers_filter)
    codes = load_cvm_codes(exclude=EXCLUDED)
    if tickers_filter:
        codes = {t: c for t, c in codes.items() if t in tickers_filter}

    # Constrói e salva coverage JSON
    coverage = build_coverage_json(records, codes)
    COVERAGE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(COVERAGE_JSON, "w", encoding="utf-8") as f:
        # sets não são serializáveis — já foram convertidos para lists em build_coverage_json
        json.dump(coverage, f, ensure_ascii=False, indent=2, default=list)
    _log(f"Coverage JSON salvo: {COVERAGE_JSON}")

    # Gera Markdown de auditoria
    if not args.no_md:
        AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
        md_content = generate_audit_md(coverage)
        with open(AUDIT_MD, "w", encoding="utf-8") as f:
            f.write(md_content)
        _log(f"Audit MD salvo: {AUDIT_MD}")

    # Sumário final no console
    summary = coverage["summary"]
    print("\n" + "=" * 60)
    print("M017-S02.5 RESULTADO FINAL")
    print("=" * 60)
    print(f"  Tickers processados : {coverage['total_tickers']}")
    print(f"  ✅ Cobertura completa: {summary['complete']}")
    print(f"  ⚠️  Cobertura parcial : {summary['partial']}")
    print(f"  ❌ Sem dados         : {summary['missing']}")
    print(f"  CSVs filtrados      : {FILTERED_BASE}")
    print(f"  Coverage JSON       : {COVERAGE_JSON}")
    print(f"  Audit MD            : {AUDIT_MD}")
    print("=" * 60)


if __name__ == "__main__":
    main()
