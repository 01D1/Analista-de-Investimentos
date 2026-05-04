"""
valuation_dcf.py
-----------------
DCF (Discounted Cash Flow) para empresas industriais e bancos.

Metodologia:
  - Industriais: FCFF (Free Cash Flow to Firm) descontado a WACC
  - Bancos: Dividendo descontado (DDM) ou Excess Return Model (ROE vs. COE)

Todas as funções retornam objetos estruturados com os cálculos intermediários
para permitir auditabilidade e análise de sensibilidade.

Unidades: R$ mil (padrão dos dados CVM). Ajustar scale se necessário.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# DCF para industriais — FCFF
# ---------------------------------------------------------------------------


@dataclass
class DCFAssumptions:
    """Premissas de entrada para o modelo DCF."""

    # WACC
    risk_free_rate: float  # Taxa livre de risco (ex: NTNB 2035 real + inflação)
    equity_risk_premium: float  # Prêmio de risco de equity (ex: 5.5%)
    beta: float  # Beta desalavancado × re-alavancado
    pre_tax_cost_of_debt: float  # Custo da dívida bruto
    tax_rate: float  # Alíquota efetiva (IR + CSLL, tipicamente 27–34%)
    debt_to_capital: float  # Dívida / (Dívida + Equity) = alavancagem alvo
    governance_premium: float = 0.0  # Prêmio adicional por governança fraca

    # Projeções (listas de comprimento n_years)
    revenue_growth: list[float] = field(default_factory=list)  # % crescimento receita
    ebitda_margin: list[float] = field(default_factory=list)  # % margem EBITDA
    capex_to_revenue: list[float] = field(default_factory=list)  # % capex/receita
    wc_to_revenue: list[float] = field(
        default_factory=list
    )  # % ΔKg/receita (positivo = saída de caixa)
    depreciation_to_revenue: list[float] = field(default_factory=list)

    # Terminal value
    terminal_growth_rate: float = 0.03  # g de perpetuidade (real + inflação)

    @property
    def cost_of_equity(self) -> float:
        return self.risk_free_rate + self.beta * self.equity_risk_premium + self.governance_premium

    @property
    def after_tax_cost_of_debt(self) -> float:
        return self.pre_tax_cost_of_debt * (1 - self.tax_rate)

    @property
    def wacc(self) -> float:
        equity_weight = 1 - self.debt_to_capital
        return (
            equity_weight * self.cost_of_equity + self.debt_to_capital * self.after_tax_cost_of_debt
        )


@dataclass
class DCFPeriod:
    """Resultado de um período projetado."""

    year: int
    revenue: float
    ebitda: float
    ebit: float
    nopat: float
    depreciation: float
    capex: float
    delta_wc: float
    fcff: float
    pv_factor: float
    pv_fcff: float


@dataclass
class DCFResult:
    """Resultado completo do modelo DCF."""

    ticker: str
    base_year: int
    assumptions: DCFAssumptions

    # Resultado por período
    periods: list[DCFPeriod] = field(default_factory=list)

    # Valores agregados
    sum_pv_fcff: float = 0.0
    terminal_ebitda: float = 0.0
    terminal_fcff: float = 0.0
    terminal_value: float = 0.0
    pv_terminal_value: float = 0.0
    enterprise_value: float = 0.0

    # Bridge EV → Equity Value
    net_debt: float = 0.0
    minority_interest: float = 0.0
    equity_value: float = 0.0
    shares_outstanding: float = 0.0
    price_target: float = 0.0

    @property
    def tv_share_of_ev(self) -> float:
        if self.enterprise_value > 0:
            return self.pv_terminal_value / self.enterprise_value
        return 0.0

    def summary(self) -> str:
        lines = [
            f"DCF — {self.ticker} (base: {self.base_year})",
            f"  WACC: {self.assumptions.wacc:.1%}   g terminal: {self.assumptions.terminal_growth_rate:.1%}",
            f"  Σ PV FCFF (projeção): R$ {self.sum_pv_fcff:,.0f}",
            f"  PV Valor Terminal:    R$ {self.pv_terminal_value:,.0f}  ({self.tv_share_of_ev:.0%} do EV)",
            f"  Enterprise Value:     R$ {self.enterprise_value:,.0f}",
            f"  (−) Dívida Líquida:   R$ {self.net_debt:,.0f}",
            f"  Equity Value:         R$ {self.equity_value:,.0f}",
        ]
        if self.shares_outstanding > 0:
            lines.append(f"  Preço-alvo:           R$ {self.price_target:.2f}")
        return "\n".join(lines)


def run_dcf(
    ticker: str,
    base_year: int,
    base_revenue: float,
    base_ebitda: float,
    assumptions: DCFAssumptions,
    net_debt: float = 0.0,
    minority_interest: float = 0.0,
    shares_outstanding: float = 0.0,
) -> DCFResult:
    """
    Executa DCF baseado em FCFF.

    Args:
        ticker: identificador da empresa
        base_year: último ano com dados reais (ex: 2025)
        base_revenue: receita do ano base (R$ mil)
        base_ebitda: EBITDA do ano base (R$ mil)
        assumptions: objeto DCFAssumptions com todas as premissas
        net_debt: dívida líquida no ano base (R$ mil)
        minority_interest: participação minoritária no balanço
        shares_outstanding: total de ações (em mil, ou unidade compatível com R$ mil)

    Returns:
        DCFResult com todos os cálculos
    """
    result = DCFResult(
        ticker=ticker,
        base_year=base_year,
        assumptions=assumptions,
        net_debt=net_debt,
        minority_interest=minority_interest,
        shares_outstanding=shares_outstanding,
    )

    n = len(assumptions.revenue_growth)
    wacc = assumptions.wacc
    tax = assumptions.tax_rate

    current_revenue = base_revenue
    sum_pv = 0.0

    for i in range(n):
        year = base_year + i + 1
        g = assumptions.revenue_growth[i]
        em = assumptions.ebitda_margin[i]
        cr = assumptions.capex_to_revenue[i]
        dr = (
            assumptions.depreciation_to_revenue[i]
            if i < len(assumptions.depreciation_to_revenue)
            else cr * 0.6
        )
        wc = assumptions.wc_to_revenue[i] if i < len(assumptions.wc_to_revenue) else 0.0

        revenue = current_revenue * (1 + g)
        ebitda = revenue * em
        depreciation = revenue * dr
        ebit = ebitda - depreciation
        nopat = ebit * (1 - tax)
        capex = revenue * cr
        delta_wc = revenue * wc

        fcff = nopat + depreciation - capex - delta_wc

        pv_factor = 1 / (1 + wacc) ** (i + 1)
        pv_fcff = fcff * pv_factor
        sum_pv += pv_fcff

        result.periods.append(
            DCFPeriod(
                year=year,
                revenue=revenue,
                ebitda=ebitda,
                ebit=ebit,
                nopat=nopat,
                depreciation=depreciation,
                capex=capex,
                delta_wc=delta_wc,
                fcff=fcff,
                pv_factor=pv_factor,
                pv_fcff=pv_fcff,
            )
        )

        current_revenue = revenue

    # Terminal Value (Gordon Growth Model sobre FCFF normalizado)
    last_period = result.periods[-1]
    terminal_fcff = last_period.fcff * (1 + assumptions.terminal_growth_rate)
    terminal_value = terminal_fcff / (wacc - assumptions.terminal_growth_rate)
    pv_terminal = terminal_value / (1 + wacc) ** n

    result.sum_pv_fcff = sum_pv
    result.terminal_ebitda = last_period.ebitda
    result.terminal_fcff = terminal_fcff
    result.terminal_value = terminal_value
    result.pv_terminal_value = pv_terminal
    result.enterprise_value = sum_pv + pv_terminal
    result.equity_value = result.enterprise_value - net_debt - minority_interest

    if shares_outstanding > 0 and result.equity_value > 0:
        result.price_target = result.equity_value / shares_outstanding

    return result


# ---------------------------------------------------------------------------
# Sensibilidade WACC × g
# ---------------------------------------------------------------------------


def sensitivity_wacc_g(
    ticker: str,
    base_year: int,
    base_revenue: float,
    base_ebitda: float,
    assumptions: DCFAssumptions,
    net_debt: float,
    shares_outstanding: float,
    wacc_range: list[float],
    g_range: list[float],
) -> dict[tuple[float, float], float]:
    """
    Retorna tabela de sensibilidade {(wacc, g): price_target}.
    """
    results = {}

    for wacc_adj in wacc_range:
        for g in g_range:
            # Criar cópia das premissas com WACC e g ajustados
            adj = DCFAssumptions(
                risk_free_rate=assumptions.risk_free_rate,
                equity_risk_premium=assumptions.equity_risk_premium,
                beta=assumptions.beta,
                pre_tax_cost_of_debt=assumptions.pre_tax_cost_of_debt,
                tax_rate=assumptions.tax_rate,
                debt_to_capital=assumptions.debt_to_capital,
                governance_premium=assumptions.governance_premium,
                revenue_growth=assumptions.revenue_growth,
                ebitda_margin=assumptions.ebitda_margin,
                capex_to_revenue=assumptions.capex_to_revenue,
                wc_to_revenue=assumptions.wc_to_revenue,
                depreciation_to_revenue=assumptions.depreciation_to_revenue,
                terminal_growth_rate=g,
            )
            # Ajustar o beta para atingir o WACC desejado
            # Solução simplificada: ajustar risk_free para deslocar o WACC
            adj.risk_free_rate = (
                wacc_adj - adj.beta * adj.equity_risk_premium - adj.governance_premium
            )

            dcf = run_dcf(
                ticker=ticker,
                base_year=base_year,
                base_revenue=base_revenue,
                base_ebitda=base_ebitda,
                assumptions=adj,
                net_debt=net_debt,
                shares_outstanding=shares_outstanding,
            )
            results[(wacc_adj, g)] = dcf.price_target

    return results


# ---------------------------------------------------------------------------
# DDM simplificado para bancos
# ---------------------------------------------------------------------------


@dataclass
class DDMResult:
    """Resultado do modelo de Dividendo Descontado."""

    ticker: str
    base_year: int
    cost_of_equity: float
    terminal_growth_rate: float

    # Projeções
    projected_dividends: list[float] = field(default_factory=list)
    pv_dividends: list[float] = field(default_factory=list)

    # Valores
    sum_pv_dividends: float = 0.0
    terminal_dividend: float = 0.0
    terminal_value: float = 0.0
    pv_terminal_value: float = 0.0
    equity_value_per_share: float = 0.0  # se dividendo já em R$/ação
    equity_value: float = 0.0


def run_ddm(
    ticker: str,
    base_year: int,
    base_net_income: float,
    payout_ratio: float,
    cost_of_equity: float,
    terminal_growth_rate: float,
    income_growth_rates: list[float],
    shares_outstanding: float = 0.0,
) -> DDMResult:
    """
    DDM simplificado para bancos.

    Projeta dividendos como: Net Income × Payout Ratio
    Desconta ao custo de equity (COE).
    """
    result = DDMResult(
        ticker=ticker,
        base_year=base_year,
        cost_of_equity=cost_of_equity,
        terminal_growth_rate=terminal_growth_rate,
    )

    coe = cost_of_equity
    current_ni = base_net_income
    sum_pv = 0.0
    n = len(income_growth_rates)

    for i, g in enumerate(income_growth_rates):
        ni = current_ni * (1 + g)
        div = ni * payout_ratio
        pv = div / (1 + coe) ** (i + 1)
        result.projected_dividends.append(div)
        result.pv_dividends.append(pv)
        sum_pv += pv
        current_ni = ni

    # Terminal value
    terminal_div = result.projected_dividends[-1] * (1 + terminal_growth_rate)
    if coe > terminal_growth_rate:
        tv = terminal_div / (coe - terminal_growth_rate)
    else:
        tv = 0.0
    pv_tv = tv / (1 + coe) ** n

    result.sum_pv_dividends = sum_pv
    result.terminal_dividend = terminal_div
    result.terminal_value = tv
    result.pv_terminal_value = pv_tv
    result.equity_value = sum_pv + pv_tv

    if shares_outstanding > 0:
        result.equity_value_per_share = result.equity_value / shares_outstanding

    return result
