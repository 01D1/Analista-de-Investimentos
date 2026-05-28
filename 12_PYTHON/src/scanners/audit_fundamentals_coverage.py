"""
audit_fundamentals_coverage.py
--------------------------------
Relatório de cobertura fundamentalista aprimorado.

Mostra por ticker:
  - Fonte de dados (DFP/LTM/ITR_PARTIAL)
  - Período mais recente disponível
  - Market cap e shares (disponível/ausente)
  - Métricas-chave disponíveis (P/L, P/VP, EV/EBITDA, ROE, etc.)
  - Alertas de plausibilidade
  - Qualidade geral (rating A/B/C/D)

Uso:
    python -m src.scanners.audit_fundamentals_coverage
    # ou:
    from src.scanners.audit_fundamentals_coverage import run_coverage_audit
    report = run_coverage_audit()
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from src.fundamentals.period_selector import select_best_period
from src.fundamentals.plausibility import PlausibilityChecker, has_critical_issues
from src.fundamentals.snapshot_from_vfi import build_snapshot_from_vfi
from src.ingestion.db import DB_PATH, get_connection
from src.utils.logger import get_logger
from src.valuation.financial_inputs_store import get_financial_inputs, list_financial_input_coverage

log = get_logger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_TICKERS_PATH = _CONFIG_DIR / "tickers.yaml"

BANK_TICKERS = frozenset({
    "ABCB4", "BBAS3", "BBDC3", "BBDC4", "BMGB4", "BPAC11",
    "BPAN4", "BRSR6", "INTR4", "ITUB4", "PINE4", "SANB11",
})


@dataclass
class TickerCoverage:
    ticker: str
    company_name: str = ""
    sector: str = ""
    is_bank: bool = False

    # Período
    has_dfp_annual: bool = False
    has_ltm: bool = False
    has_itr_only: bool = False
    period_basis: str = "NONE"
    latest_period: str = ""
    latest_fiscal_year: int = 0

    # Métricas disponíveis
    has_revenue: bool = False
    has_ebitda: bool = False
    has_net_income: bool = False
    has_equity: bool = False
    has_cash_flow: bool = False

    # Mercado
    has_market_cap: bool = False
    has_shares: bool = False
    has_pe: bool = False
    has_pb: bool = False
    has_ev_ebitda: bool = False
    has_sector_metric: bool = False  # EV/EBITDA para non-banks, P/L+P/VP para banks

    # Qualidade
    plausibility_alerts: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    data_quality_rating: str = "D"  # A/B/C/D

    def compute_rating(self) -> str:
        """Calcula rating de qualidade dos dados (A=melhor, D=sem dados)."""
        if not self.has_revenue and not self.has_net_income:
            return "D"

        score = 0
        # Período (max 30 pts)
        if self.has_dfp_annual:
            score += 30
        elif self.has_ltm:
            score += 20
        elif self.has_itr_only:
            score += 10

        # Métricas (max 30 pts)
        for flag in [self.has_revenue, self.has_ebitda, self.has_net_income,
                     self.has_equity, self.has_cash_flow]:
            if flag:
                score += 6

        # Mercado (max 25 pts)
        if self.has_market_cap:
            score += 10
        if self.has_shares:
            score += 5
        if self.has_pe:
            score += 5
        if self.has_pb:
            score += 5

        # Penalidades
        if self.has_critical_issues:
            score -= 20

        if score >= 70:
            return "A"
        elif score >= 50:
            return "B"
        elif score >= 25:
            return "C"
        else:
            return "D"


def _load_ticker_configs() -> dict[str, dict]:
    """Carrega configurações dos tickers do YAML."""
    try:
        with open(_TICKERS_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {t["ticker"].upper(): t for t in data.get("tickers", [])}
    except Exception:
        return {}


def _assess_ticker(
    ticker: str,
    ticker_config: dict,
    conn: Any,
    checker: PlausibilityChecker,
) -> TickerCoverage:
    """Gera TickerCoverage para um ticker."""
    is_bank = ticker in BANK_TICKERS or ticker_config.get("type") == "bank"

    cov = TickerCoverage(
        ticker=ticker,
        company_name=ticker_config.get("name", ""),
        sector=ticker_config.get("sector", ""),
        is_bank=is_bank,
    )

    # Checar dados VFI
    all_rows = get_financial_inputs(ticker, db_path=DB_PATH)
    if not all_rows:
        cov.data_quality_rating = "D"
        return cov

    # Checar métricas disponíveis
    metrics_present = {r["metric_name"] for r in all_rows}
    cov.has_revenue = "revenue" in metrics_present
    cov.has_ebitda = "ebitda" in metrics_present and not is_bank
    cov.has_net_income = "net_income" in metrics_present
    cov.has_equity = "equity_book_value" in metrics_present
    cov.has_cash_flow = "operating_cash_flow" in metrics_present

    # Selecionar melhor período
    sel = select_best_period(all_rows)
    if sel:
        cov.period_basis = sel.period_basis
        cov.latest_period = sel.period_end
        cov.latest_fiscal_year = sel.fiscal_year
        cov.has_dfp_annual = sel.period_basis == "DFP"
        cov.has_ltm = sel.period_basis == "LTM"
        cov.has_itr_only = sel.period_basis == "ITR_PARTIAL"

    # Checar market data
    price_row = conn.execute(
        "SELECT adj_close FROM price_ohlcv WHERE ticker=? AND is_gap=0 AND adj_close IS NOT NULL ORDER BY date DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    shares_row = conn.execute(
        "SELECT shares_outstanding FROM financial_ltm WHERE ticker=? AND shares_outstanding IS NOT NULL ORDER BY computed_date DESC LIMIT 1",
        (ticker,)
    ).fetchone()

    price = float(price_row[0]) if price_row else None
    shares = float(shares_row[0]) if shares_row else None
    cov.has_shares = shares is not None
    cov.has_market_cap = price is not None and shares is not None

    # Checar se consegue calcular multiples
    if cov.has_market_cap and cov.has_net_income:
        cov.has_pe = True
    if cov.has_market_cap and cov.has_equity:
        cov.has_pb = True
    if not is_bank and cov.has_market_cap:
        cov.has_ev_ebitda = cov.has_ebitda  # só se tiver EBITDA
    cov.has_sector_metric = (
        cov.has_ev_ebitda if not is_bank
        else (cov.has_pe and cov.has_pb)
    )

    # Plausibilidade (usando snapshot)
    try:
        snap = build_snapshot_from_vfi(ticker, period_selection=sel)
        if snap:
            alerts = checker.check(snap)
            cov.plausibility_alerts = [f"[{a.severity}] {a.check_name}" for a in alerts]
            cov.has_critical_issues = has_critical_issues(alerts)
    except Exception as exc:
        cov.plausibility_alerts = [f"[ERROR] check_failed: {exc}"]

    cov.data_quality_rating = cov.compute_rating()
    return cov


def run_coverage_audit(
    tickers: list[str] | None = None,
    db_path: Path | None = None,
    output_file: Path | None = None,
) -> dict[str, Any]:
    """
    Executa auditoria de cobertura para todos os tickers ativos.

    Args:
        tickers: Lista de tickers (usa tickers.yaml se None).
        db_path: Caminho do SQLite.
        output_file: Se fornecido, salva relatório JSON neste arquivo.

    Returns:
        Dict com resultado da auditoria.
    """
    db_path = db_path or DB_PATH
    ticker_configs = _load_ticker_configs()

    if tickers is None:
        tickers = [t for t in ticker_configs.keys() if ticker_configs[t].get("active", True)]

    conn = get_connection(db_path)
    checker = PlausibilityChecker()
    coverages: list[TickerCoverage] = []

    log.info(f"[audit_coverage] Auditando {len(tickers)} tickers...")

    for ticker in sorted(tickers):
        cfg = ticker_configs.get(ticker, {})
        try:
            cov = _assess_ticker(ticker, cfg, conn, checker)
            coverages.append(cov)
        except Exception as exc:
            log.error(f"[audit_coverage] {ticker}: erro — {exc}")
            coverages.append(TickerCoverage(ticker=ticker, data_quality_rating="D"))

    conn.close()

    # Calcular sumário
    total = len(coverages)
    summary = {
        "total_tickers": total,
        "computed_date": date.today().isoformat(),
        "by_period_basis": {
            "dfp_annual": sum(1 for c in coverages if c.has_dfp_annual),
            "ltm": sum(1 for c in coverages if c.has_ltm),
            "itr_partial": sum(1 for c in coverages if c.has_itr_only),
            "no_data": sum(1 for c in coverages if c.period_basis == "NONE"),
        },
        "by_market_data": {
            "with_market_cap": sum(1 for c in coverages if c.has_market_cap),
            "with_shares": sum(1 for c in coverages if c.has_shares),
            "with_pe": sum(1 for c in coverages if c.has_pe),
            "with_pb": sum(1 for c in coverages if c.has_pb),
            "with_ev_ebitda": sum(1 for c in coverages if c.has_ev_ebitda),
            "with_sector_metric": sum(1 for c in coverages if c.has_sector_metric),
        },
        "by_quality_rating": {
            "A": sum(1 for c in coverages if c.data_quality_rating == "A"),
            "B": sum(1 for c in coverages if c.data_quality_rating == "B"),
            "C": sum(1 for c in coverages if c.data_quality_rating == "C"),
            "D": sum(1 for c in coverages if c.data_quality_rating == "D"),
        },
        "with_plausibility_issues": sum(1 for c in coverages if c.has_critical_issues),
        "banks": sum(1 for c in coverages if c.is_bank),
        "non_banks": sum(1 for c in coverages if not c.is_bank),
    }

    result = {
        "summary": summary,
        "tickers": [
            {
                "ticker": c.ticker,
                "company_name": c.company_name,
                "sector": c.sector,
                "is_bank": c.is_bank,
                "period_basis": c.period_basis,
                "latest_period": c.latest_period,
                "latest_fiscal_year": c.latest_fiscal_year,
                "has_dfp_annual": c.has_dfp_annual,
                "has_market_cap": c.has_market_cap,
                "has_shares": c.has_shares,
                "has_pe": c.has_pe,
                "has_pb": c.has_pb,
                "has_ev_ebitda": c.has_ev_ebitda,
                "has_sector_metric": c.has_sector_metric,
                "plausibility_alerts": c.plausibility_alerts,
                "has_critical_issues": c.has_critical_issues,
                "data_quality_rating": c.data_quality_rating,
            }
            for c in coverages
        ],
    }

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"[audit_coverage] Relatório salvo em {output_file}")

    return result


def print_coverage_report(result: dict[str, Any], verbose: bool = False) -> None:
    """Imprime relatório de cobertura no terminal."""
    s = result["summary"]
    print(f"\n{'='*70}")
    print(f"  AUDITORIA DE COBERTURA FUNDAMENTALISTA — {s['computed_date']}")
    print(f"{'='*70}")
    print(f"  Total tickers: {s['total_tickers']} ({s['banks']} bancos, {s['non_banks']} industriais)\n")

    print("  📅 PERÍODO DE REFERÊNCIA:")
    pb = s["by_period_basis"]
    print(f"    DFP anual (melhor):    {pb['dfp_annual']:3d} tickers  ({pb['dfp_annual']/s['total_tickers']*100:.0f}%)")
    print(f"    LTM calculado:         {pb['ltm']:3d} tickers  ({pb['ltm']/s['total_tickers']*100:.0f}%)")
    print(f"    ITR parcial:           {pb['itr_partial']:3d} tickers  ({pb['itr_partial']/s['total_tickers']*100:.0f}%)")
    print(f"    Sem dados:             {pb['no_data']:3d} tickers")

    print("\n  💹 DADOS DE MERCADO:")
    md = s["by_market_data"]
    print(f"    Com market cap:        {md['with_market_cap']:3d} tickers")
    print(f"    Com shares_outstanding:{md['with_shares']:3d} tickers")
    print(f"    Com P/L:               {md['with_pe']:3d} tickers")
    print(f"    Com P/VP:              {md['with_pb']:3d} tickers")
    print(f"    Com EV/EBITDA:         {md['with_ev_ebitda']:3d} tickers")
    print(f"    Com métrica setorial:  {md['with_sector_metric']:3d} tickers")

    print("\n  ⭐ RATING DE QUALIDADE:")
    qr = s["by_quality_rating"]
    for grade in "ABCD":
        print(f"    {grade}: {qr.get(grade, 0):3d} tickers")

    print(f"\n  ⚠️  Com alertas críticos:   {s['with_plausibility_issues']:3d} tickers")

    if verbose:
        print(f"\n{'─'*70}")
        print("  DETALHE POR TICKER:")
        print(f"  {'TICKER':8} {'BASIS':12} {'PERÍODO':12} {'CAP':5} {'P/L':5} {'P/VP':5} {'EVEB':5} {'QUAL':5} {'ALERTAS'}")
        print(f"  {'─'*70}")
        for t in result["tickers"]:
            cap = "✓" if t["has_market_cap"] else "✗"
            pe = "✓" if t["has_pe"] else "✗"
            pb = "✓" if t["has_pb"] else "✗"
            ev = "✓" if t["has_ev_ebitda"] else ("N/A" if t["is_bank"] else "✗")
            alerts = len(t["plausibility_alerts"])
            alert_str = f"{'⚠' if t['has_critical_issues'] else ''}{alerts}" if alerts else "OK"
            print(f"  {t['ticker']:8} {t['period_basis']:12} {t['latest_period']:12} "
                  f"{cap:5} {pe:5} {pb:5} {ev:5} {t['data_quality_rating']:5} {alert_str}")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sample_only = "--sample" in sys.argv

    tickers = None
    if sample_only:
        tickers = ["PETR4", "VALE3", "ITUB4", "BBAS3", "BBDC4", "WEGE3", "EGIE3", "ABEV3", "RENT3", "PRIO3"]

    output = Path(__file__).parent.parent.parent / "reports" / "coverage_audit.json"
    result = run_coverage_audit(tickers=tickers, output_file=output)
    print_coverage_report(result, verbose=verbose)
