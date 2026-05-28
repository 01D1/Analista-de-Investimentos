"""
historical_series.py
---------------------
Geração de série histórica fundamentalista por ticker.

Fonte: valuation_financial_inputs (dados corretos, deduplicados por metric_extractor).
Hierarquia: DFP anual > ITR parcial (marcado como tal).

Métricas por ano:
  receita, ebitda, lucro_líquido, margem_ebitda, margem_líquida,
  roe, roic, dívida_líquida_ebitda, fcf, total_ativos, patrimônio_líquido

Uso:
    from src.fundamentals.historical_series import build_historical_series

    series = build_historical_series("PETR4")
    for year, data in series.items():
        print(year, data["revenue"] / 1e9, "B")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.fundamentals.period_selector import (
    PeriodSelection,
    select_best_period_for_history,
)
from src.ingestion.db import DB_PATH
from src.utils.logger import get_logger
from src.valuation.financial_inputs_store import get_financial_inputs

log = get_logger(__name__)

# Métricas de fluxo anual (DRE + DFC) — válidas apenas para DFP completo
FLOW_METRICS = {
    "revenue",
    "ebit",
    "ebitda",
    "net_income",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "depreciation_amortization",
}

# Métricas de estoque (balanço) — podem usar ITR mais recente do ano
STOCK_METRICS = {
    "total_assets",
    "current_assets",
    "non_current_assets",
    "cash_and_equivalents",
    "financial_applications",
    "gross_debt",
    "net_debt",
    "equity_book_value",
    "current_liabilities",
    "non_current_liabilities",
    "total_liabilities",
    "short_term_debt",
    "long_term_debt",
}


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _get_metrics_for_period(
    all_rows: list[dict],
    period_end: str,
    period_type: str,
) -> dict[str, float]:
    """Extrai métricas de um período específico, priorizando menor source_priority."""
    by_metric: dict[str, list[dict]] = {}
    for r in all_rows:
        if r["period_end"] != period_end or r["period_type"].upper() != period_type.upper():
            continue
        mn = r["metric_name"]
        by_metric.setdefault(mn, []).append(r)

    result: dict[str, float] = {}
    for mn, rows in by_metric.items():
        best = min(rows, key=lambda x: x.get("source_priority", 99))
        if best.get("metric_value") is not None:
            result[mn] = float(best["metric_value"])
    return result


def _derive_metrics(m: dict[str, float], is_bank: bool = False) -> dict[str, float]:
    """Calcula métricas derivadas a partir das extraídas."""
    derived = {}

    # gross_debt
    if "gross_debt" not in m:
        st = m.get("short_term_debt", 0) or 0
        lt = m.get("long_term_debt", 0) or 0
        if st or lt:
            derived["gross_debt"] = st + lt

    gd = m.get("gross_debt") or derived.get("gross_debt")

    # net_debt
    if "net_debt" not in m and gd is not None:
        cash = m.get("cash_and_equivalents", 0) or 0
        fin = m.get("financial_applications", 0) or 0
        derived["net_debt"] = gd - cash - fin

    # ebitda
    if "ebitda" not in m and not is_bank:
        ebit = m.get("ebit")
        da = m.get("depreciation_amortization")
        if ebit is not None and da is not None:
            derived["ebitda"] = ebit + abs(da)

    # free_cash_flow
    if "free_cash_flow" not in m:
        cfo = m.get("operating_cash_flow")
        capex = m.get("capex")
        if cfo is not None and capex is not None:
            derived["free_cash_flow"] = cfo - abs(capex)

    # total_liabilities
    if "total_liabilities" not in m:
        cl = m.get("current_liabilities")
        nl = m.get("non_current_liabilities")
        if cl is not None and nl is not None:
            derived["total_liabilities"] = cl + nl

    return derived


def _build_year_data(
    metrics: dict[str, float],
    selection: PeriodSelection,
    is_bank: bool,
    prev_metrics: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Constrói o dict de dados de um ano fiscal.

    Args:
        metrics: Métricas extraídas + derivadas.
        selection: PeriodSelection escolhida.
        is_bank: True para bancos (sem EV/EBITDA).
        prev_metrics: Métricas do ano anterior (para crescimento YoY).

    Returns:
        Dict com métricas, ratios e metadados de qualidade.
    """
    revenue = metrics.get("revenue")
    ebit = metrics.get("ebit")
    ebitda = None if is_bank else metrics.get("ebitda")
    net_income = metrics.get("net_income")
    cfo = metrics.get("operating_cash_flow")
    capex = metrics.get("capex")
    fcf = metrics.get("free_cash_flow")
    equity = metrics.get("equity_book_value")
    assets = metrics.get("total_assets")
    net_debt = metrics.get("net_debt")

    # Margens
    gross_margin = _safe_div(metrics.get("gross_profit"), revenue)
    ebitda_margin = _safe_div(ebitda, revenue)
    ebit_margin = _safe_div(ebit, revenue)
    net_margin = _safe_div(net_income, revenue)

    # Rentabilidade
    roe = _safe_div(net_income, equity)
    roa = _safe_div(net_income, assets)

    # ROIC
    invested_capital = (equity + net_debt) if equity is not None and net_debt is not None else None
    nopat = ebit * 0.73 if ebit is not None else None  # NOPAT = EBIT × (1 - 27%)
    roic = _safe_div(nopat, invested_capital)

    # Alavancagem
    nd_ebitda = _safe_div(net_debt, ebitda) if not is_bank else None

    # Crescimento YoY
    yoy: dict[str, Optional[float]] = {}
    if prev_metrics:
        for metric_name, field_name in [
            ("revenue", "revenue_growth"),
            ("net_income", "net_income_growth"),
            ("ebitda", "ebitda_growth"),
            ("free_cash_flow", "fcf_growth"),
            ("total_assets", "asset_growth"),
        ]:
            prev_val = prev_metrics.get(metric_name)
            curr_val = metrics.get(metric_name)
            if prev_val and curr_val and abs(prev_val) > 0:
                yoy[field_name] = (curr_val / prev_val) - 1
            else:
                yoy[field_name] = None

    data: dict[str, Any] = {
        # Identificadores
        "fiscal_year": selection.fiscal_year,
        "period_end": selection.period_end,
        "period_basis": selection.period_basis,
        "fiscal_quarter": selection.fiscal_quarter,
        "data_quality_note": selection.data_quality_note,
        "is_partial": selection.period_basis == "ITR_PARTIAL",
        "warnings": selection.warnings,

        # DRE
        "revenue": revenue,
        "ebitda": ebitda,
        "ebit": ebit,
        "net_income": net_income,

        # DFC
        "operating_cash_flow": cfo,
        "capex": capex,
        "free_cash_flow": fcf,
        "depreciation_amortization": metrics.get("depreciation_amortization"),

        # Balanço
        "total_assets": assets,
        "equity_book_value": equity,
        "gross_debt": metrics.get("gross_debt"),
        "net_debt": net_debt,
        "cash_and_equivalents": metrics.get("cash_and_equivalents"),

        # Margens
        "gross_margin": gross_margin,
        "ebitda_margin": ebitda_margin,
        "ebit_margin": ebit_margin,
        "net_margin": net_margin,

        # Rentabilidade
        "roe": roe,
        "roa": roa,
        "roic": roic,

        # Alavancagem
        "nd_ebitda": nd_ebitda,
        "nd_ebitda_is_applicable": not is_bank,

        # Crescimento
        "yoy": yoy,
    }

    return data


def build_historical_series(
    ticker: str,
    db_path: Path | None = None,
    is_bank: bool = False,
) -> dict[int, dict[str, Any]]:
    """
    Constrói série histórica anual de fundamentals para um ticker.

    Args:
        ticker: Código B3 (ex: 'PETR4').
        db_path: Caminho do SQLite.
        is_bank: True para bancos (sem EV/EBITDA, sem EBITDA como métrica principal).

    Returns:
        Dict {fiscal_year → dict_com_métricas}.
        Ordenado por ano crescente.
        Inclui period_basis para cada ano (DFP / ITR_PARTIAL).
    """
    ticker = ticker.upper()
    db_path = db_path or DB_PATH

    all_rows = get_financial_inputs(ticker, db_path=db_path)
    if not all_rows:
        log.warning(f"[historical_series] {ticker}: sem dados em valuation_financial_inputs")
        return {}

    yearly_selections = select_best_period_for_history(all_rows)
    if not yearly_selections:
        log.warning(f"[historical_series] {ticker}: sem períodos válidos")
        return {}

    series: dict[int, dict[str, Any]] = {}
    prev_metrics: dict[str, float] | None = None

    for sel in yearly_selections:
        # Tipo de período no VFI
        period_type_vfi = "DFP" if sel.period_basis == "DFP" else "ITR"

        # Extrair métricas do período
        metrics = _get_metrics_for_period(all_rows, sel.period_end, period_type_vfi)
        if not metrics:
            log.warning(f"[historical_series] {ticker} {sel.fiscal_year}: sem métricas no período {sel.period_end}")
            continue

        # Calcular métricas derivadas
        derived = _derive_metrics(metrics, is_bank=is_bank)
        metrics.update(derived)

        # Construir dados do ano
        year_data = _build_year_data(metrics, sel, is_bank=is_bank, prev_metrics=prev_metrics)
        series[sel.fiscal_year] = year_data
        prev_metrics = metrics

    return series


def build_historical_series_multi(
    tickers: list[str],
    db_path: Path | None = None,
    bank_tickers: set[str] | None = None,
) -> dict[str, dict[int, dict[str, Any]]]:
    """
    Constrói série histórica para múltiplos tickers.

    Args:
        tickers: Lista de códigos B3.
        db_path: Caminho do SQLite.
        bank_tickers: Set de tickers classificados como bancos.

    Returns:
        Dict {ticker → {fiscal_year → dict_métricas}}.
    """
    bank_tickers = bank_tickers or set()
    result: dict[str, dict[int, dict[str, Any]]] = {}
    for ticker in tickers:
        t = ticker.upper()
        try:
            series = build_historical_series(t, db_path=db_path, is_bank=(t in bank_tickers))
            result[t] = series
        except Exception as exc:
            log.error(f"[historical_series] {t}: erro — {exc}")
            result[t] = {}
    return result


def format_series_table(
    series: dict[int, dict[str, Any]],
    ticker: str,
    metrics: list[str] | None = None,
) -> str:
    """
    Formata série histórica como tabela de texto.

    Args:
        series: Saída de build_historical_series.
        ticker: Ticker para o cabeçalho.
        metrics: Métricas a exibir (default: as principais).

    Returns:
        String formatada com tabela de anos × métricas.
    """
    if not series:
        return f"{ticker}: sem dados históricos"

    if metrics is None:
        metrics = [
            "revenue", "ebitda", "net_income",
            "ebitda_margin", "net_margin", "roe", "nd_ebitda",
        ]

    years = sorted(series.keys())
    lines = [f"\n{'='*70}", f"  SÉRIE HISTÓRICA — {ticker}", f"{'='*70}"]

    # Cabeçalho
    header = f"{'Métrica':25}"
    for y in years:
        basis = series[y].get("period_basis", "?")[0]  # D, L ou I
        header += f"  {y}{basis:>1}"
    lines.append(header)
    lines.append("-" * 70)

    # Linhas de métricas
    label_map = {
        "revenue":       "Receita (B)",
        "ebitda":        "EBITDA (B)",
        "net_income":    "Lucro Líq (B)",
        "ebitda_margin": "Margem EBITDA",
        "net_margin":    "Margem Líq",
        "roe":           "ROE",
        "roic":          "ROIC",
        "nd_ebitda":     "DivLíq/EBITDA",
        "free_cash_flow":"FCF (B)",
        "total_assets":  "Ativos (B)",
        "equity_book_value": "PL (B)",
    }
    pct_metrics = {"ebitda_margin", "net_margin", "roe", "roic"}
    billion_metrics = {
        "revenue", "ebitda", "net_income", "free_cash_flow",
        "total_assets", "equity_book_value", "gross_debt", "net_debt",
    }

    for metric in metrics:
        label = label_map.get(metric, metric)
        row = f"{label:25}"
        for y in years:
            val = series[y].get(metric)
            if val is None:
                row += "    N/A"
            elif metric in pct_metrics:
                row += f"  {val:.1%}"
            elif metric in billion_metrics:
                row += f"  {val/1e9:5.1f}B"
            elif metric == "nd_ebitda":
                row += f"  {val:5.1f}x"
            else:
                row += f"  {val:7.2f}"
        lines.append(row)

    lines.append(f"{'='*70}")
    lines.append("  Legenda: D=DFP anual | L=LTM | I=ITR parcial")

    return "\n".join(lines)
