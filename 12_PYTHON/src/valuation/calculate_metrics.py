"""
calculate_metrics.py
---------------------
Cálculo de métricas financeiras a partir das demonstrações padronizadas.

Suporta tanto empresas industriais quanto bancos. Não faz download de dados
de mercado — recebe preço/shares como parâmetros quando necessário.

Módulo de "cálculo puro" — sem I/O, sem chamadas externas.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Métricas industriais
# ---------------------------------------------------------------------------


@dataclass
class IndustrialMetrics:
    """Conjunto completo de métricas para empresa industrial."""

    ticker: str
    year: int

    # Rentabilidade
    gross_margin: float | None = None  # Lucro Bruto / Receita
    ebit_margin: float | None = None  # EBIT / Receita
    ebitda_margin: float | None = None  # EBITDA / Receita
    net_margin: float | None = None  # Lucro Líquido / Receita
    roe: float | None = None  # Lucro / PL médio
    roa: float | None = None  # Lucro / Ativos médio
    roic: float | None = None  # NOPAT / Capital Investido

    # Alavancagem
    net_debt: float | None = None  # Dívida Bruta − Caixa
    nd_ebitda: float | None = None  # Dívida Líquida / EBITDA
    interest_coverage: float | None = None  # EBIT / Desp. Financeiras

    # Geração de caixa
    fcf: float | None = None  # CFO − Capex
    fcf_yield: float | None = None  # FCF / Mkt Cap (se disponível)
    fcf_conversion: float | None = None  # FCF / Lucro Líquido
    capex_to_revenue: float | None = None
    capex_to_depreciation: float | None = None

    # Crescimento (YoY)
    revenue_growth: float | None = None
    ebitda_growth: float | None = None
    net_income_growth: float | None = None
    fcf_growth: float | None = None

    # Valuação (requer dados de mercado)
    pe_ratio: float | None = None  # Preço / EPS
    ev_ebitda: float | None = None  # EV / EBITDA
    ev_ebit: float | None = None  # EV / EBIT
    pb_ratio: float | None = None  # Preço / VPA
    dividend_yield: float | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def calculate_industrial_metrics(
    ticker: str,
    year: int,
    # DRE
    net_revenue: float = 0.0,
    gross_profit: float = 0.0,
    ebit: float = 0.0,
    ebitda: float = 0.0,
    net_income: float = 0.0,
    # Balanço (corrente)
    total_assets: float = 0.0,
    shareholders_equity: float = 0.0,
    gross_debt: float = 0.0,
    cash: float = 0.0,
    # DFC
    cfo: float = 0.0,
    capex: float = 0.0,
    depreciation: float = 0.0,
    dividends_paid: float = 0.0,
    # Balanço (período anterior, para médias)
    prev_total_assets: float | None = None,
    prev_shareholders_equity: float | None = None,
    # Crescimento (requer período anterior)
    prev_net_revenue: float | None = None,
    prev_ebitda: float | None = None,
    prev_net_income: float | None = None,
    prev_fcf: float | None = None,
    # Dados de mercado (opcionais)
    market_cap: float | None = None,
    shares_outstanding: float | None = None,
    price: float | None = None,
) -> IndustrialMetrics:

    m = IndustrialMetrics(ticker=ticker, year=year)

    # Médias de balanço
    avg_assets = _avg(total_assets, prev_total_assets)
    avg_equity = _avg(shareholders_equity, prev_shareholders_equity)

    # Margens
    if net_revenue > 0:
        m.gross_margin = gross_profit / net_revenue
        m.ebit_margin = ebit / net_revenue
        m.ebitda_margin = ebitda / net_revenue
        m.net_margin = net_income / net_revenue

    # Rentabilidade
    if avg_equity > 0:
        m.roe = net_income / avg_equity
    if avg_assets > 0:
        m.roa = net_income / avg_assets

    # ROIC = NOPAT / Capital Investido
    # Capital Investido = PL + Dívida Líquida (aproximação)
    net_debt_val = gross_debt - cash
    invested_capital = shareholders_equity + net_debt_val
    if invested_capital > 0:
        # NOPAT = EBIT × (1 − alíquota efetiva)
        tax_rate = _effective_tax_rate(ebit, net_income)
        nopat = ebit * (1 - tax_rate)
        m.roic = nopat / invested_capital

    # Alavancagem
    m.net_debt = net_debt_val
    if ebitda > 0:
        m.nd_ebitda = net_debt_val / ebitda

    # FCF
    fcf = cfo - abs(capex)
    m.fcf = fcf
    if abs(depreciation) > 0:
        m.capex_to_depreciation = abs(capex) / abs(depreciation)
    if net_revenue > 0:
        m.capex_to_revenue = abs(capex) / net_revenue
    if net_income != 0:
        m.fcf_conversion = fcf / net_income

    # Crescimento YoY
    if prev_net_revenue and prev_net_revenue > 0:
        m.revenue_growth = (net_revenue / prev_net_revenue) - 1
    if prev_ebitda and abs(prev_ebitda) > 0:
        m.ebitda_growth = (ebitda / prev_ebitda) - 1
    if prev_net_income and abs(prev_net_income) > 0:
        m.net_income_growth = (net_income / prev_net_income) - 1
    if prev_fcf and abs(prev_fcf) > 0:
        m.fcf_growth = (fcf / prev_fcf) - 1

    # Valuação (somente se dados de mercado disponíveis)
    if market_cap and market_cap > 0:
        ev = market_cap + net_debt_val
        if ebitda > 0:
            m.ev_ebitda = ev / ebitda
        if ebit > 0:
            m.ev_ebit = ev / ebit
        if fcf != 0:
            m.fcf_yield = fcf / market_cap
        if dividends_paid != 0:
            m.dividend_yield = abs(dividends_paid) / market_cap

    if price and shares_outstanding and shares_outstanding > 0:
        eps = net_income / shares_outstanding
        if eps > 0:
            m.pe_ratio = price / eps
        bvps = shareholders_equity / shares_outstanding
        if bvps > 0:
            m.pb_ratio = price / bvps

    return m


# ---------------------------------------------------------------------------
# Métricas de bancos
# ---------------------------------------------------------------------------


@dataclass
class BankMetricsCalc:
    """Métricas calculadas para banco."""

    ticker: str
    year: int

    # Rentabilidade
    roe: float | None = None
    roa: float | None = None
    rote: float | None = None  # ROE sobre tangible equity
    net_margin: float | None = None

    # Qualidade de crédito
    nii_margin: float | None = None  # NII / Total Assets (NIM proxy)
    pdd_ratio: float | None = None  # PDD / Carteira de Crédito
    cost_of_credit: float | None = None  # PDD / Total Assets
    fee_share: float | None = None  # Fee Income / Total Revenues

    # Eficiência
    efficiency_ratio: float | None = None  # Despesas Operacionais / Resultado Bruto

    # Alavancagem / Capital
    leverage: float | None = None  # Assets / Equity
    loan_to_asset: float | None = None  # Carteira / Ativos

    # Crescimento
    asset_growth: float | None = None
    loan_growth: float | None = None
    net_income_growth: float | None = None
    nii_growth: float | None = None

    # Valuação
    pb_ratio: float | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None


def calculate_bank_metrics(
    ticker: str,
    year: int,
    # Income
    total_revenues: float = 0.0,
    nii_gross: float = 0.0,
    fee_income: float = 0.0,
    loan_loss_provision: float = 0.0,
    admin_expenses: float = 0.0,
    personnel_expenses: float = 0.0,
    other_op_expenses: float = 0.0,
    ebt: float = 0.0,
    net_income: float = 0.0,
    # Balance
    total_assets: float = 0.0,
    shareholders_equity: float = 0.0,
    tangible_equity: float | None = None,
    loan_portfolio_gross: float = 0.0,
    # Prior period (para médias e crescimento)
    prev_total_assets: float | None = None,
    prev_shareholders_equity: float | None = None,
    prev_loan_portfolio: float | None = None,
    prev_net_income: float | None = None,
    prev_nii: float | None = None,
    # Mercado
    market_cap: float | None = None,
    dividends_paid: float | None = None,
    shares_outstanding: float | None = None,
    price: float | None = None,
) -> BankMetricsCalc:

    m = BankMetricsCalc(ticker=ticker, year=year)

    avg_assets = _avg(total_assets, prev_total_assets)
    avg_equity = _avg(shareholders_equity, prev_shareholders_equity)
    avg_tangible = _avg(tangible_equity or shareholders_equity, None)

    # Rentabilidade
    if avg_equity > 0:
        m.roe = net_income / avg_equity
    if avg_assets > 0:
        m.roa = net_income / avg_assets
        m.nii_margin = nii_gross / avg_assets
        m.cost_of_credit = abs(loan_loss_provision) / avg_assets
    if avg_tangible and avg_tangible > 0:
        m.rote = net_income / avg_tangible
    if ebt != 0:
        m.net_margin = net_income / abs(ebt) if ebt != 0 else None

    # Qualidade de crédito
    if loan_portfolio_gross > 0:
        m.pdd_ratio = abs(loan_loss_provision) / loan_portfolio_gross
        m.loan_to_asset = loan_portfolio_gross / total_assets if total_assets > 0 else None

    # Fee share
    if total_revenues > 0 and fee_income:
        m.fee_share = abs(fee_income) / total_revenues

    # Eficiência: (Pessoal + Admin + Outras despesas operacionais) / NII + Fees
    total_op_costs = (
        abs(admin_expenses or 0) + abs(personnel_expenses or 0) + abs(other_op_expenses or 0)
    )
    net_operating_income = nii_gross + abs(fee_income or 0)
    if net_operating_income > 0 and total_op_costs > 0:
        m.efficiency_ratio = total_op_costs / net_operating_income

    # Alavancagem
    if shareholders_equity > 0 and total_assets > 0:
        m.leverage = total_assets / shareholders_equity

    # Crescimento
    if prev_total_assets and prev_total_assets > 0:
        m.asset_growth = (total_assets / prev_total_assets) - 1
    if prev_loan_portfolio and prev_loan_portfolio > 0:
        m.loan_growth = (loan_portfolio_gross / prev_loan_portfolio) - 1
    if prev_net_income and abs(prev_net_income) > 0:
        m.net_income_growth = (net_income / prev_net_income) - 1
    if prev_nii and abs(prev_nii) > 0:
        m.nii_growth = (nii_gross / prev_nii) - 1

    # Valuação
    if market_cap and market_cap > 0:
        if dividends_paid:
            m.dividend_yield = abs(dividends_paid) / market_cap
    if price and shares_outstanding and shares_outstanding > 0:
        eps = net_income / shares_outstanding
        bvps = shareholders_equity / shares_outstanding
        if eps > 0:
            m.pe_ratio = price / eps
        if bvps > 0:
            m.pb_ratio = price / bvps

    return m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _avg(current: float, previous: float | None) -> float:
    """Média entre dois períodos; retorna o valor atual se anterior ausente."""
    if previous is None or previous == 0:
        return current
    return (current + previous) / 2


def _effective_tax_rate(ebit: float, net_income: float, default: float = 0.27) -> float:
    """Estima alíquota efetiva de IR/CSLL. Retorna default se EBIT ≤ 0."""
    if ebit <= 0:
        return default
    # crude: assume net_income ≈ NOPAT; implicitly includes financial items
    # use 27% (combined IR+CSLL) as default for Brazilian companies
    return default
