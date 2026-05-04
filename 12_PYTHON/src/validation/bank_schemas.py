"""
bank_schemas.py
---------------
Pydantic v2 schemas para demonstrações financeiras de bancos brasileiros.

Estrutura CVM IFRS (COSIF adaptado):
  DRE: 3.01 = Receitas Intermediação, 3.02 = Despesas Intermediação, 3.03 = NII Bruto
  BPA: 1 = Total Ativos, 1.02.03.04 = Carteira de Crédito
  BPP: 2.03 = Passivos Financeiros, 2.08 = PL
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BankType(StrEnum):
    LARGE_BANK = "large_bank"  # Itaú, Bradesco, BB, Santander
    INVESTMENT_BANK = "investment"  # BTG Pactual
    MEDIUM_BANK = "medium"  # Inter, ABC, BMG, Pan, Pine, Banrisul
    HOLDING = "holding"  # Itaúsa
    BDR = "bdr"  # Nubank (ROXO34), Inter & Co (INTR4)


class Consolidation(StrEnum):
    CONSOLIDATED = "consolidated"
    INDIVIDUAL = "individual"


class Periodicity(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class BankMetadata(BaseModel):
    ticker: str
    company_name: str
    cvm_code: str
    period: str  # e.g. "2023A" or "2023Q4"
    bank_type: BankType
    consolidation: Consolidation
    source: str
    periodicity: Periodicity
    unit: int = 1000  # CVM default: R$ mil


# ---------------------------------------------------------------------------
# DRE Bancária (Demonstração do Resultado)
# ---------------------------------------------------------------------------


class BankIncomeStatement(BaseModel):
    # --- Receitas ---
    total_financial_revenues: float = 0.0  # 3.01 Receitas da Intermediação Financeira
    interest_income: float | None = None  # 3.01.01 Juros e Similares
    fee_income: float | None = None  # 3.01.05 Tarifas e Serviços
    insurance_result: float | None = None  # 3.01.06 Seguros e Previdência
    fx_result: float | None = None  # 3.01.04 Câmbio
    trading_result: float | None = None  # 3.01.02 Valor Justo / Trading
    other_revenues: float | None = None  # 3.01.07

    # --- Despesas ---
    total_financial_expenses: float = 0.0  # 3.02 Despesas da Intermediação Financeira
    interest_expense: float | None = None  # 3.02.01 Juros e Similares
    loan_loss_provision: float | None = None  # 3.02.02 PDD / Provisão para Perda Esperada

    # --- NII ---
    nii_gross: float = 0.0  # 3.03 Resultado Bruto da Intermediação (após PDD)

    # --- Despesas Operacionais ---
    other_operating_result: float | None = None  # 3.04 total
    admin_expenses: float | None = None  # 3.04.03 Despesas Administrativas
    tax_expenses: float | None = None  # 3.04.04 Despesas Tributárias
    personnel_expenses: float | None = None  # 3.04.02 Pessoal
    equity_income: float | None = None  # 3.04.07 Equivalência Patrimonial
    other_operating_expenses: float | None = None  # 3.04.06

    # --- Resultados ---
    ebt: float | None = None  # 3.05 Resultado Antes dos Tributos
    income_tax: float | None = None  # 3.06 IR e CSLL
    net_income_consolidated: float | None = None  # 3.07/3.09 total
    minority_interest: float | None = None  # 3.09.02
    net_income: float = 0.0  # 3.09.01 Atribuído à Controladora

    # --- Campos derivados ---
    nii_before_provision: float | None = None  # interest_income + interest_expense (negativo)
    total_operating_expenses: float | None = None

    @model_validator(mode="after")
    def calculate_derived(self) -> BankIncomeStatement:
        # NII antes da PDD
        if self.interest_income is not None and self.interest_expense is not None:
            self.nii_before_provision = self.interest_income + self.interest_expense

        # Total de despesas operacionais
        adm = self.admin_expenses or 0.0
        tax = self.tax_expenses or 0.0
        pes = self.personnel_expenses or 0.0
        self.total_operating_expenses = adm + tax + pes

        return self

    # --- Propriedades calculadas (não salvas) ---
    @property
    def nim_proxy(self) -> float | None:
        """NII bruto / Receitas totais — proxy de spread (NIM real requer ativos rentáveis)."""
        if self.total_financial_revenues and self.total_financial_revenues != 0:
            return self.nii_gross / self.total_financial_revenues
        return None

    @property
    def efficiency_ratio(self) -> float | None:
        """Índice de Eficiência = Despesas Op. / (NII_bruto + Fee Income).
        Quanto menor melhor — bancos eficientes ficam abaixo de 40%."""
        denominator = self.nii_gross + (self.fee_income or 0.0)
        if denominator and denominator != 0 and self.total_operating_expenses:
            return abs(self.total_operating_expenses) / abs(denominator)
        return None

    @property
    def cost_of_credit_ratio(self) -> float | None:
        """PDD / Receitas de Intermediação — custo do crédito."""
        if self.loan_loss_provision and self.total_financial_revenues:
            return abs(self.loan_loss_provision) / self.total_financial_revenues
        return None

    @property
    def net_margin(self) -> float | None:
        if self.total_financial_revenues and self.total_financial_revenues != 0:
            return self.net_income / self.total_financial_revenues
        return None


# ---------------------------------------------------------------------------
# Balanço Patrimonial — Ativo
# ---------------------------------------------------------------------------


class BankAssets(BaseModel):
    cash: float = 0.0  # 1.01 Caixa e Equivalentes
    total_financial_assets: float | None = None  # 1.02 Ativos Financeiros
    fv_through_pl: float | None = None  # 1.02.01 VJ através do Resultado
    fv_through_oci: float | None = None  # 1.02.02 VJ através de OCI
    amortized_cost_assets: float | None = None  # 1.02.03 Custo Amortizado
    loan_portfolio_gross: float | None = None  # 1.02.03.04 Operações de Crédito
    loan_loss_reserve: float | None = None  # 1.02.03.06 (-) Provisão para Perda
    securities: float | None = None  # 1.02.03.03/04 TVM
    compulsory_deposits: float | None = None  # 1.02.03.07 Dep. Compulsório BC
    deferred_taxes: float | None = None  # 1.03 Tributos Diferidos
    other_assets: float | None = None  # 1.04
    equity_investments: float | None = None  # 1.05 Investimentos
    ppe_net: float | None = None  # 1.06 Imobilizado
    intangibles_net: float | None = None  # 1.07 Intangível (incl. goodwill)
    total_assets: float = 0.0  # 1 Ativo Total

    @property
    def loan_portfolio_net(self) -> float | None:
        if self.loan_portfolio_gross is not None and self.loan_loss_reserve is not None:
            return self.loan_portfolio_gross + self.loan_loss_reserve  # reserve is negative
        return None

    @property
    def tangible_assets(self) -> float | None:
        if self.intangibles_net is not None:
            return self.total_assets - abs(self.intangibles_net)
        return self.total_assets


# ---------------------------------------------------------------------------
# Balanço Patrimonial — Passivo e PL
# ---------------------------------------------------------------------------


class BankLiabilities(BaseModel):
    fv_liabilities: float | None = None  # 2.01 Passivos VJ
    derivatives_liability: float | None = None  # 2.01.01
    funding_at_cost: float | None = None  # 2.03 Passivos ao Custo Amortizado
    deposits: float | None = None  # 2.03.01 Depósitos
    repo_funding: float | None = None  # 2.03.02 Captação Mercado Aberto
    interbank_funding: float | None = None  # 2.03.03 Mercados Interbancários
    institutional_funding: float | None = None  # 2.03.04 Mercados Institucionais
    provisions: float | None = None  # 2.04 Provisões
    other_liabilities: float | None = None  # 2.06 Outros Passivos
    insurance_liabilities: float | None = None  # 2.06.02 Seguros e Previdência
    total_equity: float = 0.0  # 2.08 PL Consolidado
    minority_interest_bs: float | None = None  # 2.08.09 Não Controladores
    shareholders_equity: float = 0.0  # PL atribuído à controladora
    total_liabilities_and_equity: float = 0.0  # = total_assets

    @property
    def total_funding(self) -> float | None:
        """Captação total = depósitos + mercado aberto + interbancário + institucional."""
        items = [
            self.deposits,
            self.repo_funding,
            self.interbank_funding,
            self.institutional_funding,
        ]
        valid = [x for x in items if x is not None]
        return sum(valid) if valid else None

    @model_validator(mode="after")
    def compute_shareholders_equity(self) -> BankLiabilities:
        if self.shareholders_equity == 0.0 and self.total_equity:
            minority = self.minority_interest_bs or 0.0
            self.shareholders_equity = self.total_equity - minority
        return self


# ---------------------------------------------------------------------------
# Balanço completo
# ---------------------------------------------------------------------------


class BankBalanceSheet(BaseModel):
    assets: BankAssets
    liabilities: BankLiabilities

    @property
    def leverage_ratio(self) -> float | None:
        """Total Assets / Equity — alavancagem. Bancos grandes ~10-15x."""
        if self.liabilities.shareholders_equity and self.liabilities.shareholders_equity != 0:
            return self.assets.total_assets / self.liabilities.shareholders_equity
        return None

    @property
    def book_value(self) -> float:
        return self.liabilities.shareholders_equity

    @property
    def tangible_book_value(self) -> float | None:
        intangibles = self.assets.intangibles_net or 0.0
        return self.liabilities.shareholders_equity - abs(intangibles)


# ---------------------------------------------------------------------------
# DFC — Fluxo de Caixa (simplificado para bancos)
# ---------------------------------------------------------------------------


class BankCashFlow(BaseModel):
    cfo: float = 0.0
    cfi: float = 0.0
    cff: float = 0.0
    forex_effect_on_cash: float | None = None
    dividends_paid: float | None = None
    capex: float | None = None
    beginning_cash: float = 0.0
    ending_cash: float = 0.0

    @property
    def net_cash_change(self) -> float:
        return self.cfo + self.cfi + self.cff + (self.forex_effect_on_cash or 0.0)

    @property
    def fcfe(self) -> float | None:
        """Free Cash Flow to Equity = CFO + Capex."""
        if self.capex is not None:
            return self.cfo + self.capex
        return None


# ---------------------------------------------------------------------------
# Demonstrações Completas — Banco
# ---------------------------------------------------------------------------


class BankStatements(BaseModel):
    metadata: BankMetadata
    income_statement: BankIncomeStatement
    balance_sheet: BankBalanceSheet
    cash_flow: BankCashFlow | None = None

    def summary(self) -> dict:
        i = self.income_statement
        b = self.balance_sheet
        return {
            "ticker": self.metadata.ticker,
            "period": self.metadata.period,
            "total_revenues": i.total_financial_revenues,
            "nii_gross": i.nii_gross,
            "net_income": i.net_income,
            "total_assets": b.assets.total_assets,
            "loan_portfolio": b.assets.loan_portfolio_gross,
            "deposits": b.liabilities.deposits,
            "shareholders_equity": b.liabilities.shareholders_equity,
        }


# ---------------------------------------------------------------------------
# Indicadores Bancários Calculados
# ---------------------------------------------------------------------------


class BankIndicators(BaseModel):
    ticker: str
    period: str

    # Rentabilidade
    roe: float | None = None  # Net Income / Avg Equity
    roa: float | None = None  # Net Income / Avg Total Assets
    rote: float | None = None  # Net Income / Avg Tangible Equity

    # Spread / Margem
    nim_proxy: float | None = None  # NII Bruto / Receitas Totais
    efficiency_ratio: float | None = None
    cost_of_credit: float | None = None  # PDD / Receitas

    # Resultado
    net_margin: float | None = None
    fee_income_share: float | None = None  # Fee Income / Receitas Totais

    # Balanço
    leverage: float | None = None  # Ativos / PL
    loan_to_asset: float | None = None  # Carteira / Ativos

    # Crescimento (requer período anterior)
    revenue_growth: float | None = None
    net_income_growth: float | None = None
    loan_growth: float | None = None
    equity_growth: float | None = None

    @classmethod
    def from_statements(
        cls,
        stmts: BankStatements,
        prev: BankStatements | None = None,
    ) -> BankIndicators:
        i = stmts.income_statement
        b = stmts.balance_sheet
        eq = b.liabilities.shareholders_equity or 1.0
        ta = b.assets.total_assets or 1.0

        # Se tiver período anterior, usa média
        if prev:
            prev_eq = prev.balance_sheet.liabilities.shareholders_equity or eq
            prev_ta = prev.balance_sheet.assets.total_assets or ta
            avg_eq = (eq + prev_eq) / 2
            avg_ta = (ta + prev_ta) / 2
        else:
            avg_eq = eq
            avg_ta = ta

        roe = i.net_income / avg_eq if avg_eq else None
        roa = i.net_income / avg_ta if avg_ta else None

        tbv = b.tangible_book_value
        if prev:
            prev_tbv = prev.balance_sheet.tangible_book_value or tbv
            avg_tbv = ((tbv or 0) + (prev_tbv or 0)) / 2
        else:
            avg_tbv = tbv
        rote = i.net_income / avg_tbv if avg_tbv else None

        # Crescimento
        revenue_growth = None
        net_income_growth = None
        loan_growth = None
        equity_growth = None
        if prev:
            prev_rev = prev.income_statement.total_financial_revenues
            if prev_rev and prev_rev != 0:
                revenue_growth = (i.total_financial_revenues - prev_rev) / abs(prev_rev)
            prev_ni = prev.income_statement.net_income
            if prev_ni and prev_ni != 0:
                net_income_growth = (i.net_income - prev_ni) / abs(prev_ni)
            prev_loans = prev.balance_sheet.assets.loan_portfolio_gross
            curr_loans = b.assets.loan_portfolio_gross
            if prev_loans and prev_loans != 0 and curr_loans:
                loan_growth = (curr_loans - prev_loans) / abs(prev_loans)
            prev_eq_val = prev.balance_sheet.liabilities.shareholders_equity
            if prev_eq_val and prev_eq_val != 0:
                equity_growth = (eq - prev_eq_val) / abs(prev_eq_val)

        # Participação de fees
        fee_share = None
        if i.fee_income and i.total_financial_revenues:
            fee_share = i.fee_income / i.total_financial_revenues

        # Loan to Asset
        lta = None
        if b.assets.loan_portfolio_gross and ta:
            lta = b.assets.loan_portfolio_gross / ta

        return cls(
            ticker=stmts.metadata.ticker,
            period=stmts.metadata.period,
            roe=roe,
            roa=roa,
            rote=rote,
            nim_proxy=i.nim_proxy,
            efficiency_ratio=i.efficiency_ratio,
            cost_of_credit=i.cost_of_credit_ratio,
            net_margin=i.net_margin,
            fee_income_share=fee_share,
            leverage=b.leverage_ratio,
            loan_to_asset=lta,
            revenue_growth=revenue_growth,
            net_income_growth=net_income_growth,
            loan_growth=loan_growth,
            equity_growth=equity_growth,
        )
