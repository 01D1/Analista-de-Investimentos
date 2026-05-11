"""
Financial Engine — LTM aggregation, multiples, DCF, signals orchestrator.
Reads from ingestion.db, writes to financial_* tables.

Public API:
    run_ticker(ticker) -> FinancialResult  — on-demand call from Phase 4
    run_all() -> list[FinancialResult]     — called by job_financial_engine() in scheduler

Phase 3 Plans:
    Plan 01 (this file): LTM aggregation + AccountMapper wire-up (FIN-01 partial)
    Plan 02: Multiples computation (FIN-02)
    Plan 03: DCF engine (FIN-03, FIN-04)
    Plan 04: Bank model / DDM (FIN-05)
    Plan 05: Technical signals + scheduler wiring (FIN-06, D-03)
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

import pandas as pd

from src.ingestion.db import get_connection
from src.ingestion.bcb import is_stale
from src.utils.errors import IngestionError
from src.utils.logger import get_logger
from src.valuation.sector_config import SectorConfig
from src.normalization.account_mapper import AccountMapper
from src.normalization.bank_account_mapper import BankAccountMapper

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class FinancialResult:
    ticker: str
    success: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Constants — LTM item classification
# ---------------------------------------------------------------------------

FLOW_ITEMS: frozenset[str] = frozenset({
    # Industrial
    "net_revenue",
    "ebit",
    "net_income",
    "cfo",
    "capex",
    "depreciation_amortization_cfo",
    "dividends_paid",
    # Bank / COSIF flow items
    "nii_gross",
    "loan_loss_provision",
    "fee_income",
    "total_financial_revenues",
    "total_financial_expenses",
})

SNAPSHOT_ITEMS: frozenset[str] = frozenset({
    "cash",
    "short_term_debt",
    "long_term_debt",
    "total_equity",
    "total_assets",
    "loan_portfolio_gross",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_stale_date(iso_date: str | None) -> bool:
    """Return True if date string is stale (> 1 B3 business day old)."""
    if not iso_date:
        return True
    try:
        d = datetime.fromisoformat(iso_date).date()
        return is_stale(d)
    except (ValueError, AttributeError):
        return True


# ---------------------------------------------------------------------------
# Core LTM aggregation — FIN-01
# ---------------------------------------------------------------------------


def _aggregate_ltm(
    ticker: str, conn: sqlite3.Connection, is_bank: bool
) -> dict[str, float | None]:
    """Aggregate trailing 4 ITR quarters into LTM financials dict.

    T-03-01-01 mitigation: All SQL uses parameterized queries — never f-string with ticker.

    Args:
        ticker:  B3 ticker (e.g. "PETR4")
        conn:    Open sqlite3.Connection with row_factory=sqlite3.Row
        is_bank: True → COSIF model; EBITDA set to None (Pitfall 2)

    Returns:
        dict with LTM financial items; missing keys have None values (not 0).
    """
    # Step 1: Get the 4 most recent DISTINCT reference dates for ITR
    dates = conn.execute(
        """
        SELECT DISTINCT reference_date
        FROM cvm_statements
        WHERE ticker = ? AND period_type = 'ITR' AND normalized_name IS NOT NULL
        ORDER BY reference_date DESC
        LIMIT 4
        """,
        (ticker,),
    ).fetchall()

    ltm_quarters_used = len(dates)

    if ltm_quarters_used == 0:
        log.warning(f"[{ticker}] nenhum trimestre ITR disponível")
        return {"ltm_quarters_used": 0}

    if ltm_quarters_used < 4:
        log.warning(f"[{ticker}] apenas {ltm_quarters_used} trimestre(s) ITR disponível(is)")

    ref_dates = tuple(r["reference_date"] for r in dates)

    # Step 2: Fetch all accounts for these quarters
    placeholders = ",".join("?" * len(ref_dates))
    rows = conn.execute(
        f"""
        SELECT reference_date, normalized_name, value
        FROM cvm_statements
        WHERE ticker = ? AND period_type = 'ITR'
          AND normalized_name IS NOT NULL
          AND reference_date IN ({placeholders})
        """,
        (ticker, *ref_dates),
    ).fetchall()

    # Step 3: Sum flow items; keep latest snapshot
    flow: dict[str, float] = {}
    snapshot: dict[str, dict] = {}

    # Track which items actually had rows (to distinguish "0 rows" from "no rows found")
    flow_seen: set[str] = set()
    snapshot_seen: set[str] = set()

    for row in rows:
        name = row["normalized_name"]
        val = row["value"] or 0.0
        ref = row["reference_date"]
        if name in FLOW_ITEMS:
            flow[name] = flow.get(name, 0.0) + val
            flow_seen.add(name)
        elif name in SNAPSHOT_ITEMS:
            if name not in snapshot or ref > snapshot[name]["date"]:
                snapshot[name] = {"date": ref, "value": val}
                snapshot_seen.add(name)

    result: dict[str, float | None] = dict(flow)
    for name, sv in snapshot.items():
        result[name] = sv["value"]

    # Step 4: Derive composite fields
    # EBITDA — no direct CVM code (GAP-01); derive from EBIT + D&A
    if "ebit" in flow_seen or "depreciation_amortization_cfo" in flow_seen:
        result["ebitda"] = (
            flow.get("ebit", 0.0) + flow.get("depreciation_amortization_cfo", 0.0)
        )
    else:
        result["ebitda"] = None  # DFC section absent → cannot derive

    # Pitfall 2: banks have no EBITDA concept
    if is_bank:
        result["ebitda"] = None

    # FCF — only if both CFO and capex rows were found (Pitfall 3)
    if "cfo" in flow_seen and "capex" in flow_seen:
        result["fcf"] = flow.get("cfo", 0.0) - abs(flow.get("capex", 0.0))
    else:
        result["fcf"] = None  # DFC rows absent → mark as NULL, not 0

    # Gross debt and net debt
    result["gross_debt"] = (
        snapshot.get("short_term_debt", {}).get("value", 0.0)
        + snapshot.get("long_term_debt", {}).get("value", 0.0)
    )
    result["net_debt"] = result["gross_debt"] - snapshot.get("cash", {}).get("value", 0.0)

    result["ltm_quarters_used"] = ltm_quarters_used

    return result


def _check_dfp_reconciliation(
    ticker: str, conn: sqlite3.Connection, ltm_revenue: float | None
) -> tuple[int, str | None]:
    """Compare LTM revenue to latest DFP annual. Flag if divergence > 5%.

    T-03-01-02 mitigation: Both ticker params are positional in parameterized query.
    T-03-01-04 mitigation: Uses max(abs(dfp_revenue), 1.0) to prevent division by zero.

    Returns:
        (warning_flag: 0|1, detail_message: str|None)
    """
    if ltm_revenue is None:
        return (0, None)

    row = conn.execute(
        """
        SELECT value FROM cvm_statements
        WHERE ticker = ?
          AND period_type = 'DFP'
          AND normalized_name = 'net_revenue'
          AND reference_date = (
              SELECT MAX(reference_date)
              FROM cvm_statements
              WHERE ticker = ? AND period_type = 'DFP'
          )
        LIMIT 1
        """,
        (ticker, ticker),
    ).fetchone()

    if not row or row["value"] is None:
        return (0, None)

    dfp_revenue = row["value"]
    divergence = abs(ltm_revenue - dfp_revenue) / max(abs(dfp_revenue), 1.0)

    if divergence > 0.05:
        detail = f"LTM={ltm_revenue:.0f} DFP={dfp_revenue:.0f} div={divergence:.1%}"
        log.warning(f"[{ticker}] reconciliação DFP/LTM: {detail}")
        return (1, detail)

    return (0, None)


# ---------------------------------------------------------------------------
# Back-fill normalized_name in cvm_statements — D-05
# ---------------------------------------------------------------------------


def backfill_normalized_names(conn: sqlite3.Connection) -> int:
    """Back-fill normalized_name for existing cvm_statements rows where it is NULL.

    T-03-01-05 mitigation: UPDATE uses parameterized (norm, row["id"]) — never f-string.

    Returns:
        Count of rows updated.
    """
    mapper = AccountMapper()
    rows = conn.execute(
        """
        SELECT id, account_code, account_name
        FROM cvm_statements
        WHERE normalized_name IS NULL
        """
    ).fetchall()

    updated = 0
    for row in rows:
        norm = mapper._map_row(
            pd.Series({
                "account_code": row["account_code"] or "",
                "account_name": row["account_name"] or "",
            })
        )
        if norm:
            conn.execute(
                "UPDATE cvm_statements SET normalized_name = ? WHERE id = ?",
                (norm, row["id"]),
            )
            updated += 1

    conn.commit()
    log.info(f"[backfill] normalized_name preenchido: {updated} linhas")
    return updated


# ---------------------------------------------------------------------------
# Main orchestrator — run_ticker / run_all
# ---------------------------------------------------------------------------


def run_ticker(ticker: str) -> FinancialResult:
    """Compute and persist financial engine results for a single ticker.

    Writes one row to financial_ltm keyed by (ticker, computed_date = today).
    Plans 02-05 will extend this with multiples, DCF, and signals writes.

    Returns:
        FinancialResult with success=True on success, success=False on any exception.
    """
    conn = get_connection()
    try:
        # Sector routing
        cfg = SectorConfig.for_ticker(ticker)
        is_bank = cfg.is_bank_model

        # LTM aggregation
        ltm = _aggregate_ltm(ticker, conn, is_bank)

        # DFP reconciliation check
        ltm_revenue = ltm.get("net_revenue")
        warn_flag, warn_detail = _check_dfp_reconciliation(ticker, conn, ltm_revenue)

        # Shares outstanding — yfinance metadata (best-effort, None on failure)
        shares: float | None = None
        try:
            import yfinance as yf
            yf_ticker = yf.Ticker(ticker + ".SA")
            shares = yf_ticker.info.get("sharesOutstanding")
        except Exception as exc:
            log.debug(f"[{ticker}] shares_outstanding não obtido: {exc}")

        # Write financial_ltm
        computed_date = date.today().isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO financial_ltm
            (id, ticker, computed_date, net_revenue, ebitda, net_income, fcf,
             net_debt, gross_debt, cash, shareholders_equity, shares_outstanding,
             ltm_quarters_used, ltm_reconciliation_warning, ltm_warning_detail,
             ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                ticker,
                computed_date,
                ltm.get("net_revenue"),
                ltm.get("ebitda"),
                ltm.get("net_income"),
                ltm.get("fcf"),
                ltm.get("net_debt"),
                ltm.get("gross_debt"),
                ltm.get("cash"),
                ltm.get("total_equity"),  # shareholders_equity
                shares,
                ltm.get("ltm_quarters_used"),
                warn_flag,
                warn_detail,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

        log.info(f"[{ticker}] financial_ltm gravado — quarters={ltm.get('ltm_quarters_used')}")
        return FinancialResult(ticker=ticker, success=True)

    except Exception as exc:
        log.warning(f"[{ticker}] run_ticker falhou: {exc}")
        return FinancialResult(ticker=ticker, success=False, error=str(exc))
    finally:
        conn.close()


def run_all() -> list[FinancialResult]:
    """Run the financial engine for all active tickers in tickers.yaml.

    Returns:
        List of FinancialResult (one per ticker, success or failure).
    """
    import yaml
    from pathlib import Path

    tickers_path = Path(__file__).parent.parent / "config" / "tickers.yaml"
    try:
        data = yaml.safe_load(open(tickers_path, encoding="utf-8"))
        active_tickers = [
            t["ticker"]
            for t in data.get("tickers", [])
            if t.get("active", True)
        ]
    except Exception as exc:
        log.error(f"[run_all] falha ao carregar tickers.yaml: {exc}")
        return []

    results: list[FinancialResult] = []
    for ticker in active_tickers:
        try:
            result = run_ticker(ticker)
            results.append(result)
        except Exception as exc:
            log.warning(f"[{ticker}] run_ticker excecao nao capturada: {exc}")
            results.append(FinancialResult(ticker=ticker, success=False, error=str(exc)))

    ok = sum(1 for r in results if r.success)
    log.info(f"[run_all] concluido — ok={ok} falhas={len(results)-ok}")
    return results


# ---------------------------------------------------------------------------
# Stubs — implemented in Plans 02-05
# ---------------------------------------------------------------------------


def compute_wacc(ticker: str, conn: sqlite3.Connection):
    """Compute WACC from macro_series. Implemented in Plan 03-03."""
    raise NotImplementedError("compute_wacc implemented in Plan 03-03")  # noqa: EM101


def _compute_multiples(ticker: str, conn: sqlite3.Connection, ltm: dict):
    """Compute valuation multiples. Implemented in Plan 03-02."""
    raise NotImplementedError("_compute_multiples implemented in Plan 03-02")  # noqa: EM101


def _compute_dcf(ticker: str, conn: sqlite3.Connection, ltm: dict):
    """Run DCF / DDM valuation. Implemented in Plan 03-03 / 03-04."""
    raise NotImplementedError("_compute_dcf implemented in Plans 03-03/04")  # noqa: EM101


def compute_signals(prices: "pd.Series") -> dict:
    """Compute RSI-14, MACD, MA50/200, momentum score. Implemented in Plan 03-05."""
    raise NotImplementedError("compute_signals implemented in Plan 03-05")  # noqa: EM101
