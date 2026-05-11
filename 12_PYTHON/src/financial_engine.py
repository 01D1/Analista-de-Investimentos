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
from src.valuation.calculate_metrics import calculate_industrial_metrics, calculate_bank_metrics
from src.valuation.valuation_dcf import run_ddm
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

        # FIN-02: Compute and write financial_multiples
        _compute_multiples(ticker, conn, ltm, cfg, computed_date)

        # FIN-05: Bank model routing — DDM fair value for bank tickers
        # T-03-04-01: is_bank_model is the sole gate — industrial DCF never called for banks
        if cfg.is_bank_model:
            _compute_bank_model(ticker, conn, ltm, cfg, computed_date)
        else:
            # Industrial DCF handled in Plan 03-03 (Wave 2)
            # Stub _compute_dcf remains until Wave 2 executes
            pass

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
# Price fetch helper — FIN-02
# ---------------------------------------------------------------------------


def _get_current_price(ticker: str, conn: sqlite3.Connection) -> float | None:
    """Fetch latest non-gap adj_close from price_ohlcv. Returns None if no price available.

    T-03-02-01 mitigation: parameterized query — ticker never in SQL string.
    T-03-02-04 mitigation: is_gap = 0 filter excludes NULL adj_close gap rows.
    """
    row = conn.execute(
        """
        SELECT adj_close FROM price_ohlcv
        WHERE ticker = ? AND is_gap = 0 AND adj_close IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()
    if row is None:
        log.warning(f"[{ticker}] sem preço disponível em price_ohlcv (is_gap=0)")
        return None
    return float(row["adj_close"])


# ---------------------------------------------------------------------------
# Multiples computation — FIN-02
# ---------------------------------------------------------------------------


def _compute_multiples(
    ticker: str,
    conn: sqlite3.Connection,
    ltm: dict,
    cfg: SectorConfig,
    computed_date: str,
) -> None:
    """Compute and write financial_multiples row for ticker.

    Routes to calculate_bank_metrics() for bank tickers (is_bank_model=True)
    or calculate_industrial_metrics() for industrial tickers.

    T-03-02-02 mitigation: INSERT OR REPLACE uses positional params — ticker never in SQL string.
    T-03-02-03 mitigation: None price passed through to metric functions; they return None ratios.
    """
    current_price = _get_current_price(ticker, conn)
    shares = ltm.get("shares_outstanding")

    # Use today's year as proxy for metrics year (LTM period)
    metrics_year = date.today().year

    if cfg.is_bank_model:
        # Bank path: P/BV, P/E, dividend_yield via calculate_bank_metrics()
        # EV/EBITDA is never computed for banks (FIN-05)
        metrics = calculate_bank_metrics(
            ticker=ticker,
            year=metrics_year,
            nii_gross=ltm.get("nii_gross") or 0.0,
            fee_income=ltm.get("fee_income") or 0.0,
            loan_loss_provision=ltm.get("loan_loss_provision") or 0.0,
            net_income=ltm.get("net_income") or 0.0,
            total_assets=ltm.get("total_assets") or 0.0,
            shareholders_equity=ltm.get("total_equity") or 0.0,
            loan_portfolio_gross=ltm.get("loan_portfolio_gross") or 0.0,
            shares_outstanding=shares,
            dividends_paid=ltm.get("dividends_paid"),
            price=current_price,
        )
        ev_ebitda_val = None  # FIN-05: banks never get EV/EBITDA
        ev_revenue_val = None
        # calculate_bank_metrics() has no market_cap field — compute manually
        if current_price is not None and shares is not None and shares > 0:
            market_cap_val = current_price * shares
        else:
            market_cap_val = None
    else:
        # Industrial path: P/E, EV/EBITDA, P/BV, dividend_yield, EV/Revenue
        # market_cap computed from price × shares (no market_cap param in calculate_industrial_metrics)
        if current_price is not None and shares is not None and shares > 0:
            market_cap_val = current_price * shares
        else:
            market_cap_val = None

        metrics = calculate_industrial_metrics(
            ticker=ticker,
            year=metrics_year,
            net_revenue=ltm.get("net_revenue") or 0.0,
            ebit=ltm.get("ebit") or 0.0,
            ebitda=ltm.get("ebitda") or 0.0,
            net_income=ltm.get("net_income") or 0.0,
            shareholders_equity=ltm.get("total_equity") or 0.0,
            gross_debt=ltm.get("gross_debt") or 0.0,
            cash=ltm.get("cash") or 0.0,
            cfo=ltm.get("cfo") or 0.0,
            capex=ltm.get("capex") or 0.0,
            depreciation=ltm.get("depreciation_amortization_cfo") or 0.0,
            dividends_paid=ltm.get("dividends_paid") or 0.0,
            market_cap=market_cap_val,
            shares_outstanding=shares,
            price=current_price,
        )
        ev_ebitda_val = getattr(metrics, "ev_ebitda", None)
        # EV/Revenue not in IndustrialMetrics — compute manually if we have the data
        if market_cap_val is not None and (ltm.get("net_debt") is not None):
            net_debt = ltm.get("net_debt") or 0.0
            net_rev = ltm.get("net_revenue")
            if net_rev and net_rev > 0:
                ev_revenue_val = (market_cap_val + net_debt) / net_rev
            else:
                ev_revenue_val = None
        else:
            ev_revenue_val = None

    # T-03-02-02: all INSERT params positional — ticker never interpolated into SQL
    conn.execute(
        """
        INSERT OR REPLACE INTO financial_multiples
        (id, ticker, computed_date, price, market_cap, pe_ratio, ev_ebitda,
         pb_ratio, dividend_yield, ev_revenue, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            ticker,
            computed_date,
            current_price,
            market_cap_val,
            getattr(metrics, "pe_ratio", None),
            ev_ebitda_val,
            getattr(metrics, "pb_ratio", None),
            getattr(metrics, "dividend_yield", None),
            ev_revenue_val,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    log.info(
        f"[{ticker}] multiples escritos — price={current_price} "
        f"pe={getattr(metrics, 'pe_ratio', None)}"
    )


# ---------------------------------------------------------------------------
# DCF write helper — used by Plan 03-03 (industrial DCF) and Plan 03-04 (bank DDM)
# ---------------------------------------------------------------------------


def _write_dcf_row(
    conn: sqlite3.Connection,
    ticker: str,
    computed_date: str,
    valuation_method: str,
    fair_value_brl: float | None,
    upside_pct: float | None,
    wacc: float | None,
    terminal_growth: float | None,
    selic_used: float | None,
    cds_used: float | None,
    used_fallback: bool,
    confidence_flag: str | None,
) -> None:
    """Write a row to financial_dcf. Shared by industrial DCF and bank DDM paths.

    T-03-04-03 mitigation: All params positional — ticker never interpolated into SQL.
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO financial_dcf
        (id, ticker, computed_date, valuation_method, fair_value_brl, upside_pct,
         wacc, terminal_growth, selic_used, cds_used, used_fallback, confidence_flag,
         ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            ticker,
            computed_date,
            valuation_method,
            fair_value_brl,
            upside_pct,
            wacc,
            terminal_growth,
            selic_used,
            cds_used,
            int(used_fallback),
            confidence_flag,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Bank model — FIN-05
# ---------------------------------------------------------------------------


def _compute_bank_model(
    ticker: str,
    conn: sqlite3.Connection,
    ltm: dict,
    cfg: SectorConfig,
    computed_date: str,
) -> None:
    """Compute bank DDM fair value and bank multiples.

    FIN-05: Banks use DDM (run_ddm) + bank metrics (calculate_bank_metrics).
    Never uses EBITDA, DCF FCFF, or EV/EBITDA — these are COSIF tickers.

    T-03-04-01 mitigation: is_bank_model gates all routing — enforced in run_ticker().
    T-03-04-02 mitigation: ke > terminal_growth guard before run_ddm() — avoids DDM explosion.
    T-03-04-04 mitigation: bank LTM uses BankAccountMapper (COSIF), not AccountMapper (IFRS).
    """
    # gordon_assumptions: {coe, terminal_growth, payout_ratio} — see sectors.yaml bank section
    a = cfg.gordon_assumptions
    current_price = _get_current_price(ticker, conn)
    shares = ltm.get("shares_outstanding")

    # --- DDM fair value ---
    base_net_income = ltm.get("net_income") or 0.0
    payout_ratio = float(a.get("payout_ratio", 0.40))
    terminal_growth = float(a.get("terminal_growth", 0.055))
    ke = float(a.get("coe", 0.135))  # cost of equity from gordon_assumptions

    # 5-year income growth rates — not in gordon_assumptions; use terminal_growth as proxy
    income_growth_rates = [terminal_growth] * 5

    # WACC components for metadata (used_fallback tracking via compute_wacc)
    wacc_full, selic_used, cds_used, used_fallback = compute_wacc(ticker, conn)

    fair_value = None
    confidence_flag = None

    # T-03-04-02: Guard — ke must exceed terminal_growth and a minimum floor
    if base_net_income > 0 and ke > terminal_growth and ke > 0.05:
        try:
            result = run_ddm(
                ticker=ticker,
                base_year=int(computed_date[:4]),
                base_net_income=base_net_income,
                payout_ratio=payout_ratio,
                cost_of_equity=ke,
                terminal_growth_rate=terminal_growth,
                income_growth_rates=income_growth_rates,
                shares_outstanding=shares if shares and shares > 0 else 0.0,
            )
            # DDMResult.equity_value_per_share if shares > 0; else derive from equity_value / shares
            if shares and shares > 0 and result.equity_value_per_share > 0:
                fair_value = result.equity_value_per_share
            elif shares and shares > 0 and result.equity_value > 0:
                fair_value = result.equity_value / shares
            elif result.equity_value > 0:
                fair_value = None  # no shares — cannot compute per-share price target
            else:
                fair_value = None

            # Pitfall P7: validate result range (0.1x – 5.0x current price)
            if fair_value and current_price and current_price > 0:
                ratio = fair_value / current_price
                if ratio < 0.1 or ratio > 5.0:
                    confidence_flag = "FORA DO INTERVALO CONFIAVEL"
                    log.warning(
                        f"[{ticker}] DDM: fair_value fora do intervalo esperado: "
                        f"ratio={ratio:.2f}x (fair={fair_value:.2f} price={current_price:.2f})"
                    )
        except Exception as exc:
            log.error(f"[{ticker}] run_ddm() falhou: {exc}")
            confidence_flag = "ERRO_CALCULO"
    elif ke <= terminal_growth:
        log.error(
            f"[{ticker}] DDM inválido: ke={ke:.2%} <= terminal_growth={terminal_growth:.2%}"
        )
        confidence_flag = "INPUT_INVALIDO"
    elif ke <= 0.05:
        log.error(f"[{ticker}] DDM inválido: ke={ke:.2%} <= mínimo de 5%")
        confidence_flag = "INPUT_INVALIDO"
    elif base_net_income <= 0:
        log.warning(f"[{ticker}] DDM ignorado: net_income={base_net_income} <= 0")
        confidence_flag = "SEM_LUCRO"

    upside_pct = (
        (fair_value - current_price) / current_price
        if fair_value and current_price and current_price > 0
        else None
    )

    # ebitda is None for banks — enforced in _aggregate_ltm (is_bank=True)
    # This write path stores ke (cost of equity) in the wacc column for DDM tickers
    _write_dcf_row(
        conn, ticker, computed_date, "ddm",
        fair_value, upside_pct,
        ke,              # store ke (not full WACC) in wacc column for DDM rows
        terminal_growth, selic_used, cds_used, used_fallback, confidence_flag,
    )
    log.info(
        f"[{ticker}] DDM escrito — fair_value={fair_value} "
        f"ke={ke:.3f} terminal_growth={terminal_growth:.3f} flag={confidence_flag}"
    )


# ---------------------------------------------------------------------------
# Stubs — implemented in Plans 03-05
# ---------------------------------------------------------------------------


def compute_wacc(
    ticker: str, conn: sqlite3.Connection
) -> tuple[float, float, float, bool]:
    """Compute WACC from macro_series. Implemented in Plan 03-03.

    Returns minimal fallback (wacc=0.12, selic=0.105, cds=0.015, used_fallback=True)
    so that run_ticker() remains compilable and testable before Plan 03-03.
    """
    # Minimal fallback — Plan 03-03 replaces with real macro_series lookup
    return (0.12, 0.105, 0.015, True)


def _compute_dcf(ticker: str, conn: sqlite3.Connection, ltm: dict):
    """Run DCF / DDM valuation. Implemented in Plan 03-03 / 03-04."""
    raise NotImplementedError("_compute_dcf implemented in Plans 03-03/04")  # noqa: EM101


def compute_signals(prices: "pd.Series") -> dict:
    """Compute RSI-14, MACD, MA50/200, momentum score. Implemented in Plan 03-05."""
    raise NotImplementedError("compute_signals implemented in Plan 03-05")  # noqa: EM101
