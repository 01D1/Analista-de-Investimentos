"""
schemas.py
----------
Schemas Pydantic para dados financeiros padronizados.

Define os contratos de dados entre as camadas do pipeline:
  - ExtractionMetadata   → rastreabilidade da origem
  - StatementLine        → linha individual de demonstração
  - IncomeStatement      → DRE (Demonstração do Resultado)
  - BalanceSheet         → BP (Balanço Patrimonial)
  - CashFlowStatement    → DFC (Demonstração do Fluxo de Caixa)
  - FinancialStatements  → conjunto completo das 3 demonstrações
  - FinancialIndicators  → indicadores calculados

Uso:
    from validation.schemas import FinancialStatements, ExtractionMetadata

    meta = ExtractionMetadata(
        ticker="WEGE3",
        period="2023Q4",
        consolidation="consolidated",
        currency="BRL",
        unit=1000,
        source="CVM DFP 2023",
    )
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Consolidation(StrEnum):
    CONSOLIDATED = "consolidated"  # Demonstrações consolidadas (padrão para análise)
    PARENT = "parent"  # Controladora isolada


class Currency(StrEnum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"


class Recurrence(StrEnum):
    RECURRING = "recurring"  # Item recorrente operacional
    NON_RECURRING = "non_recurring"  # Evento pontual, não se repere
    ADJUSTED = "adjusted"  # Ajuste definido pelo analista
    UNKNOWN = "unknown"  # Não classificado


class Periodicity(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    LTM = "ltm"  # Últimos 12 meses


class DocType(StrEnum):
    DFP = "DFP"
    ITR = "ITR"
    RELEASE = "release"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Metadados de extração
# ---------------------------------------------------------------------------


class ExtractionMetadata(BaseModel):
    """Rastreabilidade completa da origem dos dados."""

    ticker: str = Field(..., description="Ticker B3, ex: WEGE3")
    company_name: str | None = None
    period: str = Field(..., description="Período, ex: 2023A, 2023Q4, 2023Q1-Q3")
    reference_date: date | None = Field(None, description="Data de fechamento do período")
    periodicity: Periodicity = Periodicity.QUARTERLY
    consolidation: Consolidation = Consolidation.CONSOLIDATED
    currency: Currency = Currency.BRL
    unit: int = Field(1000, description="Multiplicador: 1=unidade, 1000=R$mil, 1_000_000=R$MM")
    doc_type: DocType = DocType.DFP
    source: str = Field(..., description="Origem, ex: CVM DFP 2023, RI WEGE3 Q4 2023")
    source_url: str | None = None
    extraction_date: date = Field(default_factory=date.today)
    notes: str | None = None

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("unit")
    @classmethod
    def unit_must_be_power_of_ten(cls, v: int) -> int:
        assert v in (1, 1_000, 1_000_000), f"unit deve ser 1, 1000 ou 1_000_000. Recebido: {v}"
        return v


# ---------------------------------------------------------------------------
# Linha de demonstração
# ---------------------------------------------------------------------------


class StatementLine(BaseModel):
    """
    Linha individual de qualquer demonstração financeira.
    Todas as linhas seguem este contrato.
    """

    account_code: str | None = Field(None, description="Código CVM/XBRL da conta")
    account_name: str = Field(..., description="Nome da conta conforme documento")
    normalized_name: str | None = Field(None, description="Nome no schema padronizado")
    value: float = Field(..., description="Valor numérico na unidade do metadado")
    recurrence: Recurrence = Recurrence.UNKNOWN
    is_parent: bool = Field(False, description="True se é linha de total/subtotal")
    notes: str | None = None


# ---------------------------------------------------------------------------
# DRE — Demonstração do Resultado
# ---------------------------------------------------------------------------


class IncomeStatement(BaseModel):
    """
    DRE padronizada.
    Valores em negativo representam redutores (deduções, custos, despesas, IR).
    """

    # Receita
    gross_revenue: float | None = Field(None, description="Receita Bruta")
    revenue_deductions: float | None = Field(None, description="Deduções da receita (negativo)")
    net_revenue: float = Field(..., description="Receita Líquida")

    # Resultado bruto
    cogs: float | None = Field(None, description="CPV/COGS (negativo)")
    gross_profit: float | None = None

    # Resultado operacional
    selling_expenses: float | None = Field(None, description="Despesas com vendas (negativo)")
    general_admin_expenses: float | None = Field(None, description="G&A (negativo)")
    other_operating_income: float | None = Field(
        None, description="Outras receitas/despesas operacionais"
    )
    equity_income: float | None = Field(None, description="Equivalência patrimonial")
    depreciation_amortization: float | None = Field(
        None, description="D&A (positivo = valor do período)"
    )
    ebit: float | None = Field(None, description="EBIT / Resultado Operacional")
    ebitda: float | None = Field(None, description="EBITDA (calculado ou informado)")
    ebitda_adjusted: float | None = Field(
        None, description="EBITDA ajustado (informado pela empresa, usar com ceticismo)"
    )

    # Resultado financeiro
    financial_income: float | None = Field(None, description="Receita financeira (positivo)")
    financial_expenses: float | None = Field(None, description="Despesa financeira (negativo)")
    net_financial_result: float | None = Field(None, description="Resultado financeiro líquido")

    # Resultado líquido
    ebt: float | None = Field(None, description="Lucro antes do IR")
    income_tax: float | None = Field(None, description="IR/CSLL (negativo)")
    net_income_consolidated: float | None = Field(None, description="Lucro líquido consolidado")
    minority_interest: float | None = Field(
        None, description="Participação de minoritários (negativo)"
    )
    net_income: float = Field(..., description="Lucro líquido atribuível à controladora")

    # Métricas derivadas (calculadas automaticamente se possível)
    gross_margin: float | None = None
    ebit_margin: float | None = None
    ebitda_margin: float | None = None
    net_margin: float | None = None

    @model_validator(mode="after")
    def calculate_derived_metrics(self) -> IncomeStatement:
        """Calcula margens e contas derivadas quando possível."""
        rev = self.net_revenue
        if rev and rev != 0:
            if self.gross_profit is not None:
                self.gross_margin = self.gross_profit / rev
            if self.ebit is not None:
                self.ebit_margin = self.ebit / rev
            if self.ebitda is not None:
                self.ebitda_margin = self.ebitda / rev
            self.net_margin = self.net_income / rev

        # Calcular gross_profit se não informado
        if self.gross_profit is None and self.cogs is not None:
            self.gross_profit = self.net_revenue + self.cogs  # cogs é negativo

        # Calcular EBITDA se D&A e EBIT disponíveis
        if (
            self.ebitda is None
            and self.ebit is not None
            and self.depreciation_amortization is not None
        ):
            self.ebitda = self.ebit + self.depreciation_amortization

        return self


# ---------------------------------------------------------------------------
# Balanço Patrimonial
# ---------------------------------------------------------------------------


class Assets(BaseModel):
    """Ativo do Balanço."""

    # Circulante
    cash: float = Field(..., description="Caixa e equivalentes")
    short_term_investments: float | None = Field(None, description="Aplicações financeiras CP")
    accounts_receivable: float | None = None
    inventories: float | None = None
    other_current_assets: float | None = None
    total_current_assets: float | None = None

    # Não circulante
    long_term_investments: float | None = Field(None, description="Aplicações financeiras LP")
    equity_investments: float | None = Field(None, description="Investimentos / Equivalência")
    ppe_net: float | None = Field(None, description="Imobilizado líquido (PP&E)")
    intangibles_net: float | None = Field(None, description="Intangível líquido")
    other_non_current_assets: float | None = None
    total_non_current_assets: float | None = None

    total_assets: float = Field(..., description="Total do Ativo")


class Liabilities(BaseModel):
    """Passivo e Patrimônio Líquido."""

    # Passivo circulante
    suppliers: float | None = None
    short_term_debt: float | None = Field(None, description="Dívida financeira CP")
    other_current_liabilities: float | None = None
    total_current_liabilities: float | None = None

    # Passivo não circulante
    long_term_debt: float | None = Field(None, description="Dívida financeira LP")
    other_non_current_liabilities: float | None = None
    total_non_current_liabilities: float | None = None

    # Patrimônio líquido
    minority_interest_bs: float | None = Field(None, description="PL de minoritários (no BP)")
    shareholders_equity: float = Field(..., description="Patrimônio líquido da controladora")
    total_equity: float | None = None

    total_liabilities_and_equity: float = Field(..., description="Total do Passivo + PL")


class BalanceSheet(BaseModel):
    """Balanço Patrimonial completo."""

    assets: Assets
    liabilities: Liabilities

    # Métricas derivadas calculadas automaticamente
    net_debt: float | None = None
    net_working_capital: float | None = None
    balance_check: bool | None = None
    balance_difference: float | None = None

    @model_validator(mode="after")
    def calculate_derived_and_check(self) -> BalanceSheet:
        a = self.assets
        liabilities_data = self.liabilities

        # Dívida líquida
        short_debt = liabilities_data.short_term_debt or 0.0
        long_debt = liabilities_data.long_term_debt or 0.0
        cash_total = a.cash + (a.short_term_investments or 0.0)
        self.net_debt = (short_debt + long_debt) - cash_total

        # Capital de giro
        if a.accounts_receivable is not None and liabilities_data.suppliers is not None:
            self.net_working_capital = (
                (a.accounts_receivable or 0)
                + (a.inventories or 0)
                - (liabilities_data.suppliers or 0)
            )

        # Verificação de equilíbrio
        diff = a.total_assets - liabilities_data.total_liabilities_and_equity
        self.balance_difference = round(diff, 2)
        self.balance_check = abs(diff) < 1.0  # tolerância de R$1

        return self


# ---------------------------------------------------------------------------
# Fluxo de Caixa
# ---------------------------------------------------------------------------


class CashFlowStatement(BaseModel):
    """DFC (método indireto)."""

    # Operacional
    net_income_cfo: float | None = Field(
        None, description="Lucro líquido (ponto de partida do CFO)"
    )
    depreciation_amortization_cfo: float | None = Field(None, description="D&A adicionada de volta")
    working_capital_changes: float | None = Field(None, description="Variação de capital de giro")
    other_operating_adjustments: float | None = None
    cfo: float = Field(..., description="Caixa das Operações (CFO)")

    # Investimentos
    capex: float | None = Field(None, description="Capex total (negativo)")
    acquisitions: float | None = Field(None, description="Aquisições (negativo)")
    asset_sales: float | None = Field(None, description="Desinvestimentos (positivo)")
    other_investing: float | None = None
    cfi: float = Field(..., description="Caixa de Investimentos (CFI)")

    # Financiamentos
    debt_issuance: float | None = Field(None, description="Captação de dívida (positivo)")
    debt_repayment: float | None = Field(None, description="Pagamento de dívida (negativo)")
    dividends_paid: float | None = Field(None, description="Dividendos pagos (negativo)")
    share_buybacks: float | None = Field(None, description="Recompra de ações (negativo)")
    other_financing: float | None = None
    cff: float = Field(..., description="Caixa de Financiamentos (CFF)")

    # Variação de caixa
    forex_effect_on_cash: float | None = Field(
        None, description="Variação cambial s/ caixa (6.04 CVM)"
    )
    beginning_cash: float = Field(..., description="Caixa inicial")
    ending_cash: float = Field(..., description="Caixa final")
    net_cash_change: float | None = None

    # Métricas derivadas
    fcff: float | None = None
    cash_check: bool | None = None

    @model_validator(mode="after")
    def calculate_derived(self) -> CashFlowStatement:
        forex = self.forex_effect_on_cash or 0.0
        self.net_cash_change = self.cfo + self.cfi + self.cff + forex

        # FCFF = CFO + capex (capex já é negativo)
        if self.capex is not None:
            self.fcff = self.cfo + self.capex

        # Verificação: CFO+CFI+CFF+forex deve bater com variação de caixa
        expected_change = self.ending_cash - self.beginning_cash
        diff = abs(self.net_cash_change - expected_change)
        self.cash_check = diff < 1.0

        return self


# ---------------------------------------------------------------------------
# Conjunto completo das 3 demonstrações
# ---------------------------------------------------------------------------


class FinancialStatements(BaseModel):
    """Conjunto das 3 demonstrações com metadados de rastreabilidade."""

    metadata: ExtractionMetadata
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlowStatement
    raw_lines: list[StatementLine] = Field(
        default_factory=list, description="Linhas brutas extraídas (para auditoria)"
    )

    def summary(self) -> dict:
        """Retorna um resumo dos principais indicadores."""
        i = self.income_statement
        b = self.balance_sheet
        c = self.cash_flow
        return {
            "ticker": self.metadata.ticker,
            "period": self.metadata.period,
            "net_revenue": i.net_revenue,
            "ebitda": i.ebitda,
            "ebit": i.ebit,
            "net_income": i.net_income,
            "ebitda_margin": i.ebitda_margin,
            "net_margin": i.net_margin,
            "net_debt": b.net_debt,
            "shareholders_equity": b.liabilities.shareholders_equity,
            "cfo": c.cfo,
            "capex": c.capex,
            "fcff": c.fcff,
            "balance_ok": b.balance_check,
            "cash_ok": c.cash_check,
        }


# ---------------------------------------------------------------------------
# Indicadores calculados
# ---------------------------------------------------------------------------


class FinancialIndicators(BaseModel):
    """
    Indicadores derivados das demonstrações.
    Calculados a partir de FinancialStatements.
    """

    ticker: str
    period: str

    # Rentabilidade
    roe: float | None = Field(None, description="Return on Equity = Lucro / PL médio")
    roic: float | None = Field(None, description="Return on Invested Capital")
    roa: float | None = Field(None, description="Return on Assets")
    nopat: float | None = Field(None, description="NOPAT = EBIT × (1 - alíquota)")

    # Margens
    gross_margin: float | None = None
    ebitda_margin: float | None = None
    ebit_margin: float | None = None
    net_margin: float | None = None

    # Alavancagem
    net_debt_ebitda: float | None = Field(None, description="Dívida Líquida / EBITDA")
    interest_coverage: float | None = Field(None, description="EBIT / Despesa Financeira")
    debt_equity: float | None = Field(None, description="Dívida Bruta / PL")

    # Eficiência
    asset_turnover: float | None = Field(None, description="Receita / Ativo médio")
    receivables_days: float | None = Field(None, description="Prazo médio de recebimento")
    inventory_days: float | None = Field(None, description="Prazo médio de estoque")
    payables_days: float | None = Field(None, description="Prazo médio de pagamento")
    cash_conversion_cycle: float | None = None

    # Geração de caixa
    fcff_margin: float | None = Field(None, description="FCFF / Receita Líquida")
    capex_revenue: float | None = Field(None, description="Capex / Receita")
    da_revenue: float | None = Field(None, description="D&A / Receita")

    @classmethod
    def from_statements(
        cls,
        current: FinancialStatements,
        previous: FinancialStatements | None = None,
        tax_rate: float = 0.34,
    ) -> FinancialIndicators:
        """
        Calcula indicadores a partir das demonstrações.

        Args:
            current: Demonstrações do período atual
            previous: Demonstrações do período anterior (para médias)
            tax_rate: Alíquota efetiva de IR (padrão 34%)
        """
        i = current.income_statement
        b = current.balance_sheet
        c = current.cash_flow
        rev = i.net_revenue

        # Médias do período (se temos o período anterior)
        avg_equity = b.liabilities.shareholders_equity
        avg_assets = b.assets.total_assets
        if previous:
            avg_equity = (avg_equity + previous.balance_sheet.liabilities.shareholders_equity) / 2
            avg_assets = (avg_assets + previous.balance_sheet.assets.total_assets) / 2

        # NOPAT
        nopat = (i.ebit * (1 - tax_rate)) if i.ebit is not None else None

        # Alavancagem
        nd_ebitda = None
        if b.net_debt is not None and i.ebitda and i.ebitda != 0:
            nd_ebitda = b.net_debt / i.ebitda

        interest_cov = None
        if i.ebit is not None and i.financial_expenses and i.financial_expenses != 0:
            interest_cov = i.ebit / abs(i.financial_expenses)

        # Eficiência (em dias)
        recv_days = None
        if i.net_revenue and i.net_revenue != 0 and b.assets.accounts_receivable is not None:
            recv_days = (b.assets.accounts_receivable / i.net_revenue) * 365

        inv_days = None
        if i.cogs and i.cogs != 0 and b.assets.inventories is not None:
            inv_days = (b.assets.inventories / abs(i.cogs)) * 365

        pay_days = None
        if i.cogs and i.cogs != 0 and b.liabilities.suppliers is not None:
            pay_days = (b.liabilities.suppliers / abs(i.cogs)) * 365

        ccc = None
        if recv_days is not None and inv_days is not None and pay_days is not None:
            ccc = recv_days + inv_days - pay_days

        return cls(
            ticker=current.metadata.ticker,
            period=current.metadata.period,
            roe=(i.net_income / avg_equity) if avg_equity and avg_equity != 0 else None,
            roa=(i.net_income / avg_assets) if avg_assets and avg_assets != 0 else None,
            nopat=nopat,
            gross_margin=i.gross_margin,
            ebitda_margin=i.ebitda_margin,
            ebit_margin=i.ebit_margin,
            net_margin=i.net_margin,
            net_debt_ebitda=nd_ebitda,
            interest_coverage=interest_cov,
            asset_turnover=(rev / avg_assets) if avg_assets and avg_assets != 0 else None,
            receivables_days=recv_days,
            inventory_days=inv_days,
            payables_days=pay_days,
            cash_conversion_cycle=ccc,
            fcff_margin=(c.fcff / rev) if c.fcff is not None and rev and rev != 0 else None,
            capex_revenue=(c.capex / rev) if c.capex is not None and rev and rev != 0 else None,
            da_revenue=(i.depreciation_amortization / rev)
            if i.depreciation_amortization and rev and rev != 0
            else None,
        )
