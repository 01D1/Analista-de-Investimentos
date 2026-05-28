"""
snapshot_from_vfi.py
---------------------
Builder de FundamentalSnapshot usando valuation_financial_inputs como fonte.

Substitui o snapshot_builder.py original que lia de cvm_statements via mapper
(que sofria de double-counting e regex imprecisas).

Vantagens desta abordagem:
  1. Lê da tabela valuation_financial_inputs — já deduplicada e validada por
     metric_extractor.py com account_code correto (não por regex).
  2. Aplica period_selector para garantir DFP > LTM > ITR_PARTIAL.
  3. Adiciona period_basis e data_quality_note ao snapshot.
  4. Nunca soma contas-pai com contas-filhas.

Métricas disponíveis em valuation_financial_inputs:
  total_assets, current_assets, cash_and_equivalents, financial_applications,
  non_current_assets, current_liabilities, non_current_liabilities,
  short_term_debt, long_term_debt, equity_book_value, revenue, ebit,
  net_income, operating_cash_flow, depreciation_amortization, capex,
  gross_debt (derivado), net_debt (derivado), ebitda (derivado),
  free_cash_flow (derivado), total_liabilities (derivado)

Uso:
    from src.fundamentals.snapshot_from_vfi import build_snapshot_from_vfi

    snap = build_snapshot_from_vfi("PETR4")
    print(snap.revenue, snap.net_income, snap.period_basis)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from src.fundamentals.period_selector import (
    PeriodBasis,
    PeriodSelection,
    select_best_period,
    select_best_period_for_history,
)
from src.fundamentals.schema import FundamentalSnapshot
from src.ingestion.db import DB_PATH, get_connection
from src.utils.logger import get_logger
from src.valuation.financial_inputs_store import get_financial_inputs

log = get_logger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_TICKERS_PATH = _CONFIG_DIR / "tickers.yaml"

# Mapeamento: metric_name em VFI → campo em FundamentalSnapshot
_VFI_TO_SNAPSHOT: dict[str, str] = {
    "revenue":                   "revenue",
    "ebit":                      "operating_income",
    "ebitda":                    "ebitda",
    "net_income":                "net_income",
    "cash_and_equivalents":      "cash",
    "gross_debt":                "debt",
    "net_debt":                  "net_debt",
    "equity_book_value":         "equity",
    "total_assets":              "assets",
    "total_liabilities":         "liabilities",
    "capex":                     "capex",
    "operating_cash_flow":       "cfo",
    "free_cash_flow":            "fcf",
    "depreciation_amortization": "_da",  # intermediária, não vai pro snapshot diretamente
}

# Bancos: sem EV/EBITDA — verificar por setor
_BANK_SECTORS: frozenset[str] = frozenset({
    "bank", "financial", "insurance", "banco", "financeiro", "seguradora",
})


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _load_ticker_meta() -> dict[str, dict[str, Any]]:
    try:
        with open(_TICKERS_PATH, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return {}
    return {row["ticker"].upper(): row for row in data.get("tickers", [])}


def _get_market_data(
    ticker: str,
    conn: sqlite3.Connection,
) -> tuple[Optional[float], Optional[float]]:
    """Retorna (price, shares_outstanding) — ou (None, None) se não disponível."""
    price_row = conn.execute(
        """
        SELECT adj_close FROM price_ohlcv
        WHERE ticker = ? AND is_gap = 0 AND adj_close IS NOT NULL
        ORDER BY date DESC LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    shares_row = conn.execute(
        """
        SELECT shares_outstanding FROM financial_ltm
        WHERE ticker = ? AND shares_outstanding IS NOT NULL
        ORDER BY computed_date DESC LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    price = float(price_row[0]) if price_row else None
    shares = float(shares_row[0]) if shares_row else None
    return price, shares


def _extract_metrics_for_period(
    rows: list[dict[str, Any]],
    period_end: str,
    period_type: str,
) -> dict[str, float]:
    """
    Extrai métricas de um conjunto de linhas VFI para um período específico.

    Para cada metric_name, pega o valor da linha com menor source_priority
    (CVM_CSV=1 é mais confiável que EXCEL_PIPELINE=2).
    """
    metrics: dict[str, float] = {}

    # Filtrar pelo período
    period_rows = [
        r for r in rows
        if r["period_end"] == period_end and r["period_type"].upper() == period_type.upper()
    ]

    # Agrupar por metric_name, pegar o de menor source_priority
    by_metric: dict[str, list[dict]] = {}
    for r in period_rows:
        mn = r["metric_name"]
        by_metric.setdefault(mn, []).append(r)

    for mn, candidates in by_metric.items():
        best = min(candidates, key=lambda x: x.get("source_priority", 99))
        if best.get("metric_value") is not None:
            metrics[mn] = float(best["metric_value"])

    return metrics


def _compute_derived_metrics(metrics: dict[str, float], is_bank: bool) -> dict[str, float]:
    """
    Calcula métricas derivadas que podem estar ausentes se a extração primária falhou.
    """
    derived = {}

    # gross_debt se ausente
    if "gross_debt" not in metrics:
        st = metrics.get("short_term_debt", 0) or 0
        lt = metrics.get("long_term_debt", 0) or 0
        if st or lt:
            derived["gross_debt"] = st + lt

    gd = metrics.get("gross_debt") or derived.get("gross_debt")

    # net_debt se ausente
    if "net_debt" not in metrics and gd is not None:
        cash = metrics.get("cash_and_equivalents", 0) or 0
        fin_app = metrics.get("financial_applications", 0) or 0
        derived["net_debt"] = gd - cash - fin_app

    # ebitda se ausente e não-banco
    if "ebitda" not in metrics and not is_bank:
        ebit = metrics.get("ebit")
        da = metrics.get("depreciation_amortization")
        if ebit is not None and da is not None:
            derived["ebitda"] = ebit + abs(da)

    # free_cash_flow se ausente
    if "free_cash_flow" not in metrics:
        cfo = metrics.get("operating_cash_flow")
        capex = metrics.get("capex")
        if cfo is not None and capex is not None:
            derived["free_cash_flow"] = cfo - abs(capex)

    # total_liabilities se ausente
    if "total_liabilities" not in metrics:
        cl = metrics.get("current_liabilities")
        nl = metrics.get("non_current_liabilities")
        if cl is not None and nl is not None:
            derived["total_liabilities"] = cl + nl

    return derived


def build_snapshot_from_vfi(
    ticker: str,
    db_path: Optional[Path] = None,
    period_selection: Optional[PeriodSelection] = None,
) -> Optional[FundamentalSnapshot]:
    """
    Constrói FundamentalSnapshot a partir da tabela valuation_financial_inputs.

    Args:
        ticker: Código B3 do ativo.
        db_path: Caminho do SQLite (usa DB_PATH padrão se None).
        period_selection: Seleção de período pré-computada. Se None, chama
                          select_best_period internamente.

    Returns:
        FundamentalSnapshot com dados corretos, ou None se sem dados.
    """
    ticker = ticker.upper()
    db_path = db_path or DB_PATH

    # Carregar todos os inputs financeiros do ticker
    all_rows = get_financial_inputs(ticker, db_path=db_path)
    if not all_rows:
        log.warning(f"[snapshot_from_vfi] {ticker}: sem dados em valuation_financial_inputs")
        return None

    # Selecionar melhor período se não fornecido
    if period_selection is None:
        period_selection = select_best_period(all_rows)
        if period_selection is None:
            log.warning(f"[snapshot_from_vfi] {ticker}: nenhum período válido encontrado")
            return None

    # Carregar metadados do ticker
    ticker_meta = _load_ticker_meta().get(ticker, {})
    company_name = ticker_meta.get("name")
    sector = ticker_meta.get("sector")
    industry = ticker_meta.get("type") or ticker_meta.get("industry") or "industrial"
    is_bank = str(industry).lower() in {"bank", "banco"} or str(sector or "").lower() in _BANK_SECTORS

    # Extrair métricas do período selecionado
    conn = get_connection(db_path)
    try:
        price, shares = _get_market_data(ticker, conn)
    finally:
        conn.close()

    # Métricas diretas do VFI
    period_type = "DFP" if period_selection.period_basis == "DFP" else "ITR"
    if period_selection.period_basis == "LTM":
        # Para LTM: usar o ITR mais recente para balanço e calcular DRE via LTM
        period_type = "ITR"

    metrics = _extract_metrics_for_period(all_rows, period_selection.period_end, period_type)

    # Métricas derivadas
    derived = _compute_derived_metrics(metrics, is_bank)
    metrics.update(derived)

    # Para LTM: calcular receita/lucro via LTM clássico
    if period_selection.period_basis == "LTM" and len(period_selection.ltm_quarters) == 3:
        prior_dfp_end, prior_itr_end, curr_itr_end = period_selection.ltm_quarters
        _apply_ltm_flow_metrics(metrics, all_rows, prior_dfp_end, prior_itr_end, curr_itr_end)

    # Mapear métricas para FundamentalSnapshot
    revenue = metrics.get("revenue")
    operating_income = metrics.get("ebit")
    ebitda = None if is_bank else metrics.get("ebitda")
    net_income = metrics.get("net_income")
    cash = metrics.get("cash_and_equivalents")
    debt = metrics.get("gross_debt")
    net_debt = metrics.get("net_debt")
    equity = metrics.get("equity_book_value")
    assets = metrics.get("total_assets")
    liabilities = metrics.get("total_liabilities")
    capex = metrics.get("capex")
    cfo = metrics.get("operating_cash_flow")
    fcf = metrics.get("free_cash_flow")

    # Métricas de mercado
    market_cap = price * shares if price and shares else None
    enterprise_value = (market_cap + net_debt) if market_cap and net_debt is not None else None

    # Ratios derivados
    gross_margin = _safe_div(metrics.get("revenue"), metrics.get("revenue"))  # placeholder
    ebitda_margin = _safe_div(ebitda, revenue)
    net_margin = _safe_div(net_income, revenue)
    roe = _safe_div(net_income, equity)
    roa = _safe_div(net_income, assets)

    invested_capital = None
    if equity is not None and net_debt is not None:
        invested_capital = equity + net_debt
    roic = _safe_div(operating_income, invested_capital) if invested_capital else None

    debt_ebitda = _safe_div(net_debt, ebitda) if not is_bank else None
    eps = _safe_div(net_income, shares) if shares else None

    # Gross margin
    gross_profit = metrics.get("gross_profit")
    gross_margin = _safe_div(gross_profit, revenue)

    # Valuation multiples
    pe = _safe_div(market_cap, net_income)
    pb = _safe_div(market_cap, equity)
    ev_ebitda = None if is_bank else _safe_div(enterprise_value, ebitda)
    ev_ebit = None if is_bank else _safe_div(enterprise_value, operating_income)
    ev_revenue = None if is_bank else _safe_div(enterprise_value, revenue)
    fcf_yield = _safe_div(fcf, market_cap) if market_cap else None

    # Qualidade do dado
    quality_metrics = {
        "period_basis": period_selection.period_basis,
        "period_end": period_selection.period_end,
        "data_quality_note": period_selection.data_quality_note,
        "warnings": period_selection.warnings,
        "is_bank_model": is_bank,
        "has_market_data": price is not None and shares is not None,
        "metrics_extracted": len(metrics),
        "has_ebitda": ebitda is not None,
        "has_cash_flow": cfo is not None,
        "source": "valuation_financial_inputs",
    }

    valuation_multiples: dict[str, Any] = {}
    if not is_bank:
        if pe is not None:
            valuation_multiples["pe"] = pe
        if pb is not None:
            valuation_multiples["pb"] = pb
        if ev_ebitda is not None:
            valuation_multiples["ev_ebitda"] = ev_ebitda
        if ev_ebit is not None:
            valuation_multiples["ev_ebit"] = ev_ebit
        if ev_revenue is not None:
            valuation_multiples["ev_revenue"] = ev_revenue
        if fcf_yield is not None:
            valuation_multiples["fcf_yield"] = fcf_yield
    else:
        # Bancos: apenas P/L e P/VP
        if pe is not None:
            valuation_multiples["pe"] = pe
        if pb is not None:
            valuation_multiples["pb"] = pb
        valuation_multiples["ev_ebitda"] = None  # N/A para bancos
        valuation_multiples["ev_ebit"] = None     # N/A para bancos

    sector_metrics: dict[str, Any] = {
        "industry": industry,
        "is_bank": is_bank,
    }

    return FundamentalSnapshot(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        industry=industry,
        period_type=period_selection.period_basis,  # DFP / LTM / ITR_PARTIAL
        fiscal_year=period_selection.fiscal_year,
        fiscal_quarter=period_selection.fiscal_quarter,
        reference_date=period_selection.period_end,
        revenue=revenue,
        gross_profit=gross_profit,
        ebitda=ebitda,
        operating_income=operating_income,
        net_income=net_income,
        cash=cash,
        debt=debt,
        equity=equity,
        assets=assets,
        liabilities=liabilities,
        capex=capex,
        cfo=cfo,
        fcf=fcf,
        shares_outstanding=shares,
        eps=eps,
        roe=roe,
        roic=roic,
        roa=roa,
        gross_margin=gross_margin,
        ebitda_margin=ebitda_margin,
        net_margin=net_margin,
        debt_ebitda=debt_ebitda,
        net_debt=net_debt,
        enterprise_value=enterprise_value,
        market_cap=market_cap,
        valuation_multiples=valuation_multiples,
        quality_metrics=quality_metrics,
        sector_metrics=sector_metrics,
        source_trace={"period_selection": {
            "basis": period_selection.period_basis,
            "period_end": period_selection.period_end,
            "fiscal_year": period_selection.fiscal_year,
            "note": period_selection.data_quality_note,
        }},
    )


def _apply_ltm_flow_metrics(
    metrics: dict[str, float],
    all_rows: list[dict[str, Any]],
    prior_dfp_end: str,
    prior_itr_end: str,
    curr_itr_end: str,
) -> None:
    """
    Calcula métricas de fluxo LTM e atualiza o dict metrics in-place.

    LTM = DFP(N-1) + ITR_YTD(N) - ITR_YTD(N-1)

    Aplica apenas para métricas de fluxo (DRE + DFC):
      revenue, ebit, net_income, operating_cash_flow, capex, ebitda
    """
    flow_metrics = [
        "revenue", "ebit", "net_income",
        "operating_cash_flow", "capex", "depreciation_amortization",
    ]

    dfp_m = _extract_metrics_for_period(all_rows, prior_dfp_end, "DFP")
    prior_itr_m = _extract_metrics_for_period(all_rows, prior_itr_end, "ITR")
    curr_itr_m = _extract_metrics_for_period(all_rows, curr_itr_end, "ITR")

    for metric in flow_metrics:
        dfp_val = dfp_m.get(metric)
        prior_itr_val = prior_itr_m.get(metric)
        curr_itr_val = curr_itr_m.get(metric)

        if dfp_val is None or prior_itr_val is None or curr_itr_val is None:
            continue

        ltm_val = dfp_val + curr_itr_val - prior_itr_val
        metrics[metric] = ltm_val

    # Recalcular EBITDA LTM se EBIT e D&A disponíveis
    ebit = metrics.get("ebit")
    da = metrics.get("depreciation_amortization")
    if ebit is not None and da is not None:
        metrics["ebitda"] = ebit + abs(da)

    # Recalcular FCF LTM
    cfo = metrics.get("operating_cash_flow")
    capex = metrics.get("capex")
    if cfo is not None and capex is not None:
        metrics["free_cash_flow"] = cfo - abs(capex)


def build_all_snapshots_from_vfi(
    tickers: list[str],
    db_path: Optional[Path] = None,
) -> dict[str, Optional[FundamentalSnapshot]]:
    """
    Constrói snapshots para uma lista de tickers.

    Returns:
        Dict {ticker → FundamentalSnapshot | None}
    """
    results: dict[str, Optional[FundamentalSnapshot]] = {}
    for ticker in tickers:
        try:
            snap = build_snapshot_from_vfi(ticker, db_path=db_path)
            results[ticker] = snap
        except Exception as exc:
            log.error(f"[snapshot_from_vfi] {ticker}: erro — {exc}", exc_info=True)
            results[ticker] = None
    return results


def build_historical_snapshots_from_vfi(
    ticker: str,
    db_path: Optional[Path] = None,
) -> list[FundamentalSnapshot]:
    """
    Constrói série histórica anual de snapshots para um ticker.

    Usa select_best_period_for_history para garantir DFP por ano quando disponível.

    Returns:
        Lista de FundamentalSnapshot ordenada por fiscal_year ASC.
    """
    ticker = ticker.upper()
    db_path = db_path or DB_PATH

    all_rows = get_financial_inputs(ticker, db_path=db_path)
    if not all_rows:
        return []

    yearly_selections = select_best_period_for_history(all_rows)
    snapshots: list[FundamentalSnapshot] = []

    for sel in yearly_selections:
        snap = build_snapshot_from_vfi(ticker, db_path=db_path, period_selection=sel)
        if snap is not None:
            snapshots.append(snap)

    return snapshots
