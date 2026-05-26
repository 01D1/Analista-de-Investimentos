"""
metric_extractor.py
-------------------
M017-S03 — Metric Extraction Engine

Reads from cvm_statements (already ingested in M017-S02) and extracts
structured financial metrics into valuation_financial_inputs.

Supports:
  - Non-bank (IFRS) tickers: BPA/BPP/DRE/DFC with standard account codes
    + account_name validation to avoid false matches
  - Bank (COSIF) tickers: adapted equity lookup + keyword-based D&A/CapEx

Target metrics (direct):
  total_assets, current_assets, cash_and_equivalents, financial_applications,
  non_current_assets, current_liabilities, non_current_liabilities,
  short_term_debt, long_term_debt, equity_book_value, revenue, ebit,
  net_income, operating_cash_flow, depreciation_amortization, capex

Target metrics (derived):
  gross_debt, net_debt, ebitda, free_cash_flow, total_liabilities

Periods:
  - DFP: one record per fiscal year (reference_date = YYYY-12-31)
  - ITR: one record per quarter end (reference_date = YYYY-03-31, 06-30, 09-30)
  - Both use unit='units' (values already scaled in cvm_statements)

Usage:
    from src.ingestion.metric_extractor import extract_ticker, extract_all

    # Canary dry-run
    results = extract_ticker('EGIE3', write=False)

    # Persist
    results = extract_ticker('EGIE3', write=True)

    # All tickers
    summary = extract_all(tickers=['EGIE3', 'PETR4'], write=True)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from src.ingestion.db import DB_PATH, get_connection
from src.valuation.financial_inputs_store import (
    ensure_financial_inputs_schema,
    upsert_financial_input,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

# ── Source metadata ─────────────────────────────────────────────────────────────

SOURCE_TYPE = "CVM_CSV"
SOURCE_PRIORITY = 1

# ── Bank tickers (COSIF — different BPP account structure) ─────────────────────

BANK_TICKERS: frozenset[str] = frozenset({
    "ABCB4", "BBAS3", "BBDC3", "BBDC4", "BMGB4", "BPAC11",
    "BPAN4", "BRSR6", "INTR4", "ITUB4", "PINE4", "SANB11",
})

# ── Account code maps — NON-BANK (IFRS) ────────────────────────────────────────

# BPA: assets (same for banks and non-banks)
BPA_CODES: dict[str, str] = {
    "1":       "total_assets",
    "1.01":    "current_assets",
    "1.01.01": "cash_and_equivalents",
    "1.01.02": "financial_applications",
    "1.02":    "non_current_assets",
}

# BPP: liabilities + equity (NON-BANK only)
BPP_CODES_NON_BANK: dict[str, str] = {
    "2.01":    "current_liabilities",
    "2.01.04": "short_term_debt",
    "2.02":    "non_current_liabilities",
    "2.02.01": "long_term_debt",
    "2.03":    "equity_book_value",
}

# Name validation for BPP — at least one keyword must appear in account_name
# (prevents bank COSIF codes from being misextracted)
BPP_NAME_VALIDATION: dict[str, list[str]] = {
    "2.01.04": ["empréstim", "financiament"],
    "2.02.01": ["empréstim", "financiament"],
    "2.03":    ["patrimônio"],
}

# DRE: income statement (works for banks and non-banks)
DRE_CODES: dict[str, str] = {
    "3.01": "revenue",
    "3.05": "ebit",
    "3.11": "net_income",
}

# Name validation for DRE
DRE_NAME_VALIDATION: dict[str, list[str]] = {
    "3.11": ["lucro", "prejuízo"],
}

# DFC: operating cash flow (same for all)
DFC_DIRECT_CODES: dict[str, str] = {
    "6.01": "operating_cash_flow",
}

# ── Keyword patterns ────────────────────────────────────────────────────────────

# D&A: search in 6.01.01.xx (depth-4 codes)
DA_KEYWORDS: list[str] = ["deprecia", "amortiza", "exaustão"]

# CapEx: search in 6.02.xx (depth-3 codes)
# Only negative values are summed (outflows). Positive values (asset sales) are ignored.
# Keywords ordered by specificity:
CAPEX_INCLUDE_KW: list[str] = [
    "imobilizado", "intangível", "ativo fixo",
    "propriedade, planta",
    "ativo não circulante",  # IGTI11 style: "Aquisições de Ativo Não Circulante"
    "ativo permanente",      # older CVM terminology for non-current assets
    "aquisição de ativo",    # generic acquisitions — watch for M&A payment exclusion below
]
CAPEX_EXCLUDE_KW: list[str] = [
    "venda", "alienação", "descontinuad",
    "combinação de negóci", "aquisição de empresa", "compra de empresa",
    "obrigações vinculadas",  # installment payments on past acquisitions
    "aquisição de subsidiár",  # M&A
    "aquisição de partici",    # M&A / equity investments
]

# Equity for banks: search in 2.xx short codes
EQUITY_BANK_KW: list[str] = ["patrimônio líquid"]

# Net income fallback (when 3.11 name-validation fails): search 3.xx short codes
NET_INCOME_FALLBACK_KW: list[str] = ["lucro/prejuízo consolidado", "lucro ou prejuízo"]
NET_INCOME_FALLBACK_EXCLUDE: list[str] = ["por ação", "operações"]


# ── Helpers ────────────────────────────────────────────────────────────────────

AccountMap = Dict[str, Dict[str, Any]]  # code → {value, name}


def _code_depth(code: str) -> int:
    """Number of dot-separated parts in an account code.

    '6.01.01.03' → 4; '2.03' → 2
    """
    return len(code.split("."))


def _find_kw(
    accounts: AccountMap,
    prefix: str,
    required_depth: int,
    include_kw: list[str],
    exclude_kw: Optional[list[str]] = None,
) -> list[tuple[str, float, str]]:
    """Find accounts matching prefix + depth + keyword criteria.

    Returns list of (code, value, name) tuples for matching accounts.
    """
    matches = []
    for code, acc in accounts.items():
        if not code.startswith(prefix):
            continue
        if _code_depth(code) != required_depth:
            continue
        name_lower = acc["name"].lower()
        if not any(kw in name_lower for kw in include_kw):
            continue
        if exclude_kw and any(kw in name_lower for kw in exclude_kw):
            continue
        matches.append((code, acc["value"], acc["name"]))
    return matches


def _find_equity_bank(accounts: AccountMap) -> tuple[str, Optional[float], str]:
    """Find equity_book_value for banks via keyword search on short 2.xx codes."""
    candidates = []
    for code, acc in accounts.items():
        if not code.startswith("2."):
            continue
        if _code_depth(code) > 2:  # only 2.XX, not 2.XX.YY
            continue
        name_lower = acc["name"].lower()
        if any(kw in name_lower for kw in EQUITY_BANK_KW):
            candidates.append((code, acc["value"], acc["name"]))
    if not candidates:
        return ("", None, "")
    # Take shortest code (most aggregate)
    candidates.sort(key=lambda x: len(x[0]))
    return candidates[0]


def _find_net_income_fallback(accounts: AccountMap) -> tuple[str, Optional[float], str]:
    """Fallback net income when 3.11 name-validation fails."""
    candidates = []
    for code, acc in accounts.items():
        if not code.startswith("3."):
            continue
        if _code_depth(code) > 2:
            continue
        name_lower = acc["name"].lower()
        if any(kw in name_lower for kw in NET_INCOME_FALLBACK_KW):
            if not any(xkw in name_lower for xkw in NET_INCOME_FALLBACK_EXCLUDE):
                candidates.append((code, acc["value"], acc["name"]))
    if not candidates:
        return ("", None, "")
    candidates.sort(key=lambda x: len(x[0]))
    return candidates[0]


def _find_da(accounts: AccountMap) -> tuple[str, Optional[float], str]:
    """Find D&A from 6.01.01.xx codes with keyword matching. Returns sum."""
    matches = _find_kw(accounts, "6.01.01.", 4, DA_KEYWORDS)
    if not matches:
        return ("", None, "")
    total_val = sum(v for _, v, _ in matches if v is not None)
    codes = "+".join(c for c, _, _ in matches)
    names = "; ".join(n for _, _, n in matches)
    return (codes, total_val, names)


def _find_capex(accounts: AccountMap) -> tuple[str, Optional[float], str]:
    """Find CapEx from 6.02.xx codes with keyword matching.

    Returns abs(sum of NEGATIVE values) — only outflows are counted.
    Positive values (asset sales accidentally matching keywords) are excluded.
    """
    matches = _find_kw(
        accounts, "6.02.", 3, CAPEX_INCLUDE_KW, CAPEX_EXCLUDE_KW
    )
    if not matches:
        return ("", None, "")
    # Only sum negative (outflow) values — ignore asset-sale proceeds
    outflows = [(c, v, n) for c, v, n in matches if v is not None and v < 0]
    if not outflows:
        return ("", None, "")
    raw_sum = sum(v for _, v, _ in outflows)
    capex_abs = abs(raw_sum) if raw_sum != 0 else None
    codes = "+".join(c for c, _, _ in outflows)
    names = "; ".join(n for _, _, n in outflows)
    return (codes, capex_abs, names)


def _quarter_from_date(date_str: str) -> Optional[int]:
    """'2024-09-30' → 3; '2024-12-31' → None (DFP annual)."""
    month = int(date_str[5:7])
    return {3: 1, 6: 2, 9: 3}.get(month)


def _fiscal_year_from_date(date_str: str) -> int:
    return int(date_str[:4])


# ── Core extraction ────────────────────────────────────────────────────────────

def _extract_period_metrics(
    accounts: AccountMap,
    is_bank: bool,
    ticker: str,
    period_end: str,
    period_type: str,
    source_path: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Extract all metrics for a single (ticker, period_end, period_type) period.

    Args:
        accounts: dict of account_code → {value, name} for this period.
        is_bank: True if ticker is in BANK_TICKERS.
        ticker: B3 ticker code.
        period_end: YYYY-MM-DD string (DT_FIM_EXERC).
        period_type: 'DFP' or 'ITR'.
        source_path: optional path for provenance.

    Returns:
        List of valuation_financial_inputs record dicts (without 'id').
    """
    fiscal_year = _fiscal_year_from_date(period_end)
    fiscal_quarter = _quarter_from_date(period_end)

    results: list[dict[str, Any]] = []
    extracted: dict[str, float] = {}

    def add(
        metric_name: str,
        value: Optional[float],
        account_code: str,
        account_name: str,
        extraction_method: str = "structured",
        confidence: float = 1.0,
        statement_type: Optional[str] = None,
    ) -> None:
        if value is None:
            return
        record = {
            "ticker":            ticker,
            "period_type":       period_type,
            "period_end":        period_end,
            "fiscal_year":       fiscal_year,
            "fiscal_quarter":    fiscal_quarter,
            "metric_name":       metric_name,
            "metric_value":      value,
            "currency":          "BRL",
            "unit":              "units",
            "source_type":       SOURCE_TYPE,
            "source_priority":   SOURCE_PRIORITY,
            "source_path":       source_path,
            "source_doc_id":     None,
            "statement_type":    statement_type,
            "account_code":      account_code,
            "account_name":      account_name,
            "confidence":        confidence,
            "extraction_method": extraction_method,
        }
        results.append(record)
        extracted[metric_name] = value

    # ── BPA (assets) — identical for banks and non-banks ──────────────────────
    for code, metric in BPA_CODES.items():
        acc = accounts.get(code)
        if acc and acc["value"] is not None:
            add(metric, acc["value"], code, acc["name"], statement_type="BPA")

    # ── BPP (liabilities + equity) ─────────────────────────────────────────────
    if not is_bank:
        for code, metric in BPP_CODES_NON_BANK.items():
            acc = accounts.get(code)
            if acc and acc["value"] is not None:
                validators = BPP_NAME_VALIDATION.get(code, [])
                name_lower = acc["name"].lower()
                if not validators or any(v in name_lower for v in validators):
                    add(metric, acc["value"], code, acc["name"], statement_type="BPP")
    else:
        # Banks: keyword-based equity search
        eq_code, eq_val, eq_name = _find_equity_bank(accounts)
        if eq_val is not None:
            add("equity_book_value", eq_val, eq_code, eq_name,
                statement_type="BPP", confidence=0.95)

    # ── DRE (income statement) ─────────────────────────────────────────────────
    for code, metric in DRE_CODES.items():
        acc = accounts.get(code)
        if acc and acc["value"] is not None:
            validators = DRE_NAME_VALIDATION.get(code, [])
            name_lower = acc["name"].lower()
            if not validators or any(v in name_lower for v in validators):
                add(metric, acc["value"], code, acc["name"], statement_type="DRE")
            elif metric == "net_income":
                # Fallback: keyword search for net income
                fb_code, fb_val, fb_name = _find_net_income_fallback(accounts)
                if fb_val is not None:
                    add(metric, fb_val, fb_code, fb_name,
                        statement_type="DRE", confidence=0.9,
                        extraction_method="keyword")

    # Also run fallback if 3.11 wasn't in accounts at all
    if "net_income" not in extracted:
        fb_code, fb_val, fb_name = _find_net_income_fallback(accounts)
        if fb_val is not None:
            add("net_income", fb_val, fb_code, fb_name,
                statement_type="DRE", confidence=0.85,
                extraction_method="keyword")

    # ── DFC (cash flow) ───────────────────────────────────────────────────────
    for code, metric in DFC_DIRECT_CODES.items():
        acc = accounts.get(code)
        if acc and acc["value"] is not None:
            add(metric, acc["value"], code, acc["name"], statement_type="DFC")

    # D&A
    da_code, da_val, da_name = _find_da(accounts)
    if da_val is not None:
        add("depreciation_amortization", da_val, da_code, da_name,
            statement_type="DFC", extraction_method="keyword")

    # CapEx
    capex_code, capex_val, capex_name = _find_capex(accounts)
    if capex_val is not None:
        add("capex", capex_val, capex_code, capex_name,
            statement_type="DFC", extraction_method="keyword")

    # ── Derived metrics ───────────────────────────────────────────────────────
    # gross_debt
    if "short_term_debt" in extracted and "long_term_debt" in extracted:
        gross = extracted["short_term_debt"] + extracted["long_term_debt"]
        add("gross_debt", gross, "2.01.04+2.02.01", "Empréstimos CP + LP",
            extraction_method="derived")

    # net_debt
    if "gross_debt" in extracted:
        cash = extracted.get("cash_and_equivalents", 0) or 0
        fin_apps = extracted.get("financial_applications", 0) or 0
        net_debt = extracted["gross_debt"] - cash - fin_apps
        add("net_debt", net_debt, "derived", "Dívida Bruta - Caixa - Aplicações",
            extraction_method="derived")

    # ebitda
    if "ebit" in extracted and "depreciation_amortization" in extracted:
        ebitda = extracted["ebit"] + extracted["depreciation_amortization"]
        add("ebitda", ebitda, "3.05+DA", "EBIT + Depreciação e Amortização",
            extraction_method="derived")

    # free_cash_flow = operating_cash_flow - capex (capex already abs-valued)
    if "operating_cash_flow" in extracted and "capex" in extracted:
        fcf = extracted["operating_cash_flow"] - extracted["capex"]
        add("free_cash_flow", fcf, "6.01-capex", "FCO - CapEx",
            extraction_method="derived")

    # total_liabilities
    if "current_liabilities" in extracted and "non_current_liabilities" in extracted:
        total_liab = extracted["current_liabilities"] + extracted["non_current_liabilities"]
        add("total_liabilities", total_liab, "2.01+2.02", "Passivo Circulante + Não Circulante",
            extraction_method="derived")

    return results


# ── Data loading ────────────────────────────────────────────────────────────────

def _load_ticker_accounts(
    ticker: str,
    conn: sqlite3.Connection,
) -> dict[tuple[str, str], AccountMap]:
    """Query cvm_statements for a ticker and build period → AccountMap.

    Deduplication strategy:
      - Filter rows where year = YEAR(reference_date): this selects only ÚLTIMO
        (current-year) records for DFP and avoids re-counting the PENÚLTIMO
        comparative from a later DFP filing.
      - For each (reference_date, period_type, account_code), deduplicate by
        (account_name, value) to prevent cross-filing renumbering artifacts
        (e.g., same account appearing as 6.02.09 in DFP-2024 and as 6.02.11
        in DFP-2025 comparative).

    Returns dict keyed by (reference_date, period_type).
    """
    rows = conn.execute(
        """
        SELECT
            reference_date,
            period_type,
            account_code,
            account_name,
            value
        FROM cvm_statements
        WHERE ticker = ?
          AND reference_date IS NOT NULL
          AND account_code IS NOT NULL
          AND value IS NOT NULL
          -- Keep only the "ÚLTIMO" (current-year) records: filing year must match
          -- the reference date year. This eliminates PENÚLTIMO cross-filing dups.
          AND CAST(SUBSTR(reference_date, 1, 4) AS INTEGER) = year
        GROUP BY reference_date, period_type, account_code
        ORDER BY reference_date, period_type, account_code
        """,
        (ticker,),
    ).fetchall()

    periods: dict[tuple[str, str], AccountMap] = {}
    for row in rows:
        ref_date, ptype, code, name, value = row
        key = (ref_date, ptype)
        if key not in periods:
            periods[key] = {}
        periods[key][code] = {"value": value, "name": name or ""}

    return periods


# ── Public API ──────────────────────────────────────────────────────────────────

def extract_ticker(
    ticker: str,
    write: bool = False,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Extract all financial metrics for a ticker from cvm_statements.

    Args:
        ticker: B3 ticker code (e.g., 'EGIE3'). Case-insensitive.
        write: If True, write to valuation_financial_inputs. Default False (dry-run).
        db_path: Optional SQLite path override.

    Returns:
        dict with:
            ticker, is_bank, periods_processed, metrics_extracted,
            metrics_upserted, skipped (by name), errors (list of str)
    """
    ticker = ticker.upper()
    db_path = db_path or DB_PATH
    is_bank = ticker in BANK_TICKERS

    summary: dict[str, Any] = {
        "ticker":            ticker,
        "is_bank":           is_bank,
        "periods_processed": 0,
        "metrics_extracted": 0,
        "metrics_upserted":  0,
        "skipped":           {},
        "errors":            [],
    }

    if write:
        ensure_financial_inputs_schema(db_path)

    conn = get_connection(db_path)
    try:
        periods = _load_ticker_accounts(ticker, conn)
    finally:
        conn.close()

    if not periods:
        log.warning(f"[metric_extractor] {ticker}: no data found in cvm_statements")
        summary["errors"].append("no data in cvm_statements")
        return summary

    all_records: list[dict[str, Any]] = []

    for (ref_date, period_type), accounts in sorted(periods.items()):
        try:
            records = _extract_period_metrics(
                accounts=accounts,
                is_bank=is_bank,
                ticker=ticker,
                period_end=ref_date,
                period_type=period_type,
                source_path=str(db_path),
            )
            all_records.extend(records)
            summary["periods_processed"] += 1
            summary["metrics_extracted"] += len(records)
        except Exception as exc:
            msg = f"{period_type} {ref_date}: {exc}"
            log.error(f"[metric_extractor] {ticker} ERROR — {msg}")
            summary["errors"].append(msg)

    # Count what metrics were extracted across all periods
    metric_counts: dict[str, int] = {}
    for r in all_records:
        mn = r["metric_name"]
        metric_counts[mn] = metric_counts.get(mn, 0) + 1

    # Upsert
    for record in all_records:
        try:
            result = upsert_financial_input(record, db_path=db_path, write=write)
            if result.get("action") in ("upserted", "dry_run"):
                summary["metrics_upserted"] += 1
        except Exception as exc:
            msg = f"upsert {record.get('metric_name')} {record.get('period_end')}: {exc}"
            log.error(f"[metric_extractor] {ticker} UPSERT ERROR — {msg}")
            summary["errors"].append(msg)

    summary["metric_counts"] = metric_counts
    log.info(
        f"[metric_extractor] {ticker} — "
        f"periods={summary['periods_processed']} "
        f"records={summary['metrics_extracted']} "
        f"write={write} errors={len(summary['errors'])}"
    )
    return summary


def extract_all(
    tickers: Optional[list[str]] = None,
    write: bool = False,
    db_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Extract metrics for multiple tickers.

    Args:
        tickers: Optional list of ticker codes. If None, reads from tickers.yaml.
        write: Persist to DB. Default False (dry-run).
        db_path: Optional SQLite path.
        config_path: Optional tickers.yaml path override.

    Returns:
        dict with:
            total_tickers, total_records, total_errors, ticker_summaries (list),
            missing_metrics (dict: metric → tickers without it)
    """
    if tickers is None:
        cfg_path = config_path or (Path(__file__).parents[2] / "config" / "tickers.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        ticker_list = cfg.get("tickers", cfg)
        tickers = [
            t["ticker"] for t in ticker_list
            if isinstance(t, dict) and t.get("active", True)
        ]

    tickers_upper = [t.upper() for t in tickers]

    global_summary: dict[str, Any] = {
        "total_tickers":  len(tickers_upper),
        "total_records":  0,
        "total_errors":   0,
        "ticker_summaries": [],
        "missing_metrics":  {},
    }

    # Key metrics every ticker should have
    KEY_METRICS = {
        "total_assets", "equity_book_value", "revenue",
        "net_income", "operating_cash_flow",
    }

    for ticker in tickers_upper:
        result = extract_ticker(ticker, write=write, db_path=db_path)
        global_summary["ticker_summaries"].append(result)
        global_summary["total_records"]  += result["metrics_upserted"]
        global_summary["total_errors"]   += len(result["errors"])

        found_metrics = set(result.get("metric_counts", {}).keys())
        for m in KEY_METRICS:
            if m not in found_metrics:
                global_summary["missing_metrics"].setdefault(m, []).append(ticker)

    return global_summary
