"""
bank_account_mapper.py
-----------------------
Mapeamento de contas CVM para bancos brasileiros (estrutura IFRS/COSIF).

Estratégia:
  1. Código exato (ex: "3.01" → "total_financial_revenues")
  2. Prefixo (ex: "3.01.01" → "interest_income")
  3. Fallback por regex no nome da conta (útil para variações entre bancos)

Diferenças da estrutura industrial:
  - 3.01 = Receitas da Intermediação Financeira (≠ Receita Líquida industrial)
  - 3.02 = Despesas da Intermediação (inclui PDD)
  - 3.03 = Resultado Bruto (NII após PDD)
  - BP não tem Ativo Circulante/Não Circulante — tudo financeiro
  - PL está em 2.08 (não 2.03 como industrial)
"""

from __future__ import annotations

import re

import pandas as pd

# ---------------------------------------------------------------------------
# Mapeamento principal de contas CVM para bancos
# ---------------------------------------------------------------------------

BANK_ACCOUNT_MAP: dict[str, str] = {
    # ====== DRE ======
    # Receitas
    "3.01": "total_financial_revenues",
    "3.01.01": "interest_income",
    "3.01.02": "trading_result",  # VJ através do Resultado
    "3.01.04": "fx_result",  # Resultado de Câmbio
    "3.01.05": "fee_income",  # Tarifas e Serviços
    "3.01.06": "insurance_result",  # Seguros
    "3.01.07": "other_revenues",
    # Despesas de intermediação
    "3.02": "total_financial_expenses",
    "3.02.01": "interest_expense",
    "3.02.02": "loan_loss_provision",  # PDD / Perda Esperada com Crédito
    "3.02.03": "other_provision",  # Perda com demais ativos
    # NII Bruto
    "3.03": "nii_gross",
    # Despesas operacionais
    "3.04": "other_operating_result",
    "3.04.01": "fee_income_other",  # Receitas de Serviços (alguns bancos colocam aqui)
    "3.04.02": "personnel_expenses",
    "3.04.03": "admin_expenses",
    "3.04.04": "tax_expenses",
    "3.04.05": "other_operating_revenues",
    "3.04.06": "other_operating_expenses",
    "3.04.07": "equity_income",
    # Resultado final
    "3.05": "ebt",  # Resultado Antes dos Tributos
    "3.06": "income_tax",  # IR e CSLL
    "3.06.01": "income_tax_current",
    "3.06.02": "income_tax_deferred",
    "3.07": "net_income_consolidated",  # Operações Continuadas
    "3.08": "discontinued_ops",
    "3.09": "net_income_consolidated",
    "3.09.01": "net_income",  # Atribuído à Controladora (Itaú, BTG)
    "3.09.02": "minority_interest",
    # Alternativa: BB, Bradesco, Santander usam 3.11.01 (não 3.09.01)
    "3.11": "net_income_consolidated",
    "3.11.01": "net_income",  # Atribuído à Controladora (BB, Bradesco, SANB)
    "3.11.02": "minority_interest",
    # Equivalência patrimonial — alguns bancos colocam em 3.04.08 (BB, Bradesco)
    "3.04.08": "equity_income",
    # ====== BPA (Ativo) ======
    "1": "total_assets",
    "1.01": "cash",
    "1.02": "total_financial_assets",
    # Itaú / BTG: 1.02.01 = VJ Resultado, 1.02.02 = VJ OCI, 1.02.03 = Custo Amortizado
    "1.02.01": "fv_through_pl",
    "1.02.02": "fv_through_oci",
    "1.02.03": "amortized_cost_assets",
    "1.02.03.01": "interbank_deposits_asset",
    "1.02.03.02": "repo_assets",
    "1.02.03.03": "securities",
    "1.02.03.04": "loan_portfolio_gross",  # Operações de Crédito (Itaú, BTG)
    "1.02.03.05": "other_financial_assets",
    "1.02.03.06": "loan_loss_reserve",  # (-) Provisão (Itaú)
    "1.02.03.07": "compulsory_deposits",
    "1.02.03.08": "voluntary_bc_deposits",
    # BB: 1.02.01 = Dep.Compulsório, 1.02.02 = VJ, 1.02.03 = VJ OCI, 1.02.04 = Custo Amortizado
    "1.02.04": "amortized_cost_assets_alt",
    "1.02.04.04": "loan_portfolio_gross",  # Operações de Crédito (BB, Bradesco)
    "1.02.04.05": "loan_loss_reserve",  # Provisão (BB)
    "1.03": "deferred_taxes",
    "1.04": "other_assets",
    "1.05": "equity_investments",
    "1.06": "ppe_net",
    "1.07": "intangibles_net",
    # ====== BPP (Passivo e PL) ======
    # Nota: layout varia bastante entre bancos (Itaú usa 2.03/2.08, BB usa 2.02/2.07).
    # Para campos ambíguos, o fallback por nome de conta (BANK_NAME_PATTERNS) é mais robusto.
    "2": "total_liabilities_and_equity",
    "2.01": "fv_liabilities",
    "2.01.01": "derivatives_liability",
    # Itaú / BTG: 2.03 = Passivos ao Custo Amortizado, 2.08 = PL Consolidado
    "2.03": "funding_at_cost",
    "2.03.01": "deposits",
    "2.03.02": "repo_funding",
    "2.03.03": "interbank_funding",
    "2.03.04": "institutional_funding",
    "2.03.05": "other_funding",
    "2.04": "provisions",
    "2.05": "tax_liabilities",
    "2.06": "other_liabilities",
    "2.06.02": "insurance_liabilities",
    "2.08": "total_equity",  # PL Consolidado (Itaú, BTG, Bradesco, SANB)
    "2.08.01": "share_capital",
    "2.08.02": "capital_reserves",
    "2.08.04": "profit_reserves",
    "2.08.09": "minority_interest_bs",  # Não Controladores (Itaú usa .09)
    "2.08.10": "minority_interest_bs",  # Alguns usam .10
    # BB usa 2.02 = Custo Amortizado e 2.07 = PL — resolvido via nome de conta (ver BANK_NAME_PATTERNS)
    # ====== DFC ======
    "6.01": "cfo",
    "6.02": "cfi",
    "6.02.02": "capex",
    "6.03": "cff",
    "6.03.04": "dividends_paid",
    "6.04": "forex_effect_on_cash",
    "6.05.01": "beginning_cash",
    "6.05.02": "ending_cash",
}

# Variações de nomes de conta (fallback regex)
BANK_NAME_PATTERNS: list[tuple[re.Pattern, str]] = [
    # DRE
    (re.compile(r"receitas? da intermediação financeira", re.I), "total_financial_revenues"),
    (re.compile(r"receitas? de juros? e similares?", re.I), "interest_income"),
    (re.compile(r"receitas? de (prestação de serviços?|tarifas? bancárias?)", re.I), "fee_income"),
    (re.compile(r"resultado de (contratos? de )?(seguro|previdência)", re.I), "insurance_result"),
    (re.compile(r"resultado (de operações? de câmbio|de variação cambial)", re.I), "fx_result"),
    (
        re.compile(r"resultado de ativos? e passivos? financeiros?.*valor justo", re.I),
        "trading_result",
    ),
    (re.compile(r"despesas? da intermediação financeira", re.I), "total_financial_expenses"),
    (re.compile(r"despesas? de juros? e similares?", re.I), "interest_expense"),
    (re.compile(r"(perda|provisão).*operações? de crédito", re.I), "loan_loss_provision"),
    (re.compile(r"resultado bruto (da )?intermediação financeira", re.I), "nii_gross"),
    (re.compile(r"despesas? de pessoal", re.I), "personnel_expenses"),
    (re.compile(r"(outras? )?despesas? administrativas?", re.I), "admin_expenses"),
    (re.compile(r"despesas? tributárias?", re.I), "tax_expenses"),
    (re.compile(r"resultado da equivalência patrimonial", re.I), "equity_income"),
    (re.compile(r"resultado antes? (dos? tributos?|do ir)", re.I), "ebt"),
    (re.compile(r"imposto de renda e contribuição social", re.I), "income_tax"),
    (
        re.compile(r"resultado líquido das? operações? (continuadas?|descontinuadas?)", re.I),
        "net_income_consolidated",
    ),
    (re.compile(r"(lucro|prejuízo) consolidado do período", re.I), "net_income_consolidated"),
    (re.compile(r"atribuído (a |ao )?sócios? da empresa controladora", re.I), "net_income"),
    (re.compile(r"atribuído (a |aos? )?sócios? não controladores?", re.I), "minority_interest"),
    # BPA
    (re.compile(r"caixa e equivalentes? de caixa", re.I), "cash"),
    (re.compile(r"ativos? financeiros? total", re.I), "total_financial_assets"),
    (re.compile(r"operações? de crédito e arrendamento mercantil", re.I), "loan_portfolio_gross"),
    (re.compile(r"\(-\) provisão para perda esperada", re.I), "loan_loss_reserve"),
    (re.compile(r"depósitos? compulsórios? no banco central", re.I), "compulsory_deposits"),
    (re.compile(r"tributos? diferidos?", re.I), "deferred_taxes"),
    (re.compile(r"imobilizado( de uso)?", re.I), "ppe_net"),
    (re.compile(r"intangíveis?|goodwill", re.I), "intangibles_net"),
    (re.compile(r"^ativo total$", re.I), "total_assets"),
    # BPP — depósitos e captações (vários layouts)
    (re.compile(r"^depósitos?$", re.I), "deposits"),
    (re.compile(r"captaç(ão|ões) no mercado aberto", re.I), "repo_funding"),
    (re.compile(r"captaç(ão|ões) .*mercado aberto", re.I), "repo_funding"),
    (re.compile(r"recursos? de mercados? interbancários?", re.I), "interbank_funding"),
    (re.compile(r"recursos? de mercados? institucionais?", re.I), "institutional_funding"),
    (re.compile(r"passivos? financeiros? ao custo amortizado", re.I), "funding_at_cost"),
    (re.compile(r"provisões?$", re.I), "provisions"),
    # PL — múltiplos layouts (Itaú: 2.08, BB: 2.07, cada banco com nome ligeiramente diferente)
    (re.compile(r"patrimônio líquido consolidado", re.I), "total_equity"),
    (
        re.compile(r"patrimônio líquido atribuído ao controlador[a]?$", re.I),
        "shareholders_equity_direct",
    ),
    (
        re.compile(r"patrimônio líquido atribuído (a )?sócios? da empresa controladora", re.I),
        "shareholders_equity_direct",
    ),
    (re.compile(r"participação dos? acionistas? não controladores?", re.I), "minority_interest_bs"),
    (
        re.compile(r"patrimônio líquido atribuído (a )?sócios? não controladores?", re.I),
        "minority_interest_bs",
    ),
    (re.compile(r"^passivo total$", re.I), "total_liabilities_and_equity"),
]


class BankAccountMapper:
    """
    Mapeia DataFrame CVM (CD_CONTA + DS_CONTA + VL_CONTA) para dicionário
    de campos padronizados para bancos.
    """

    def to_dict(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Converte DataFrame de demonstração para dicionário {campo: valor}.

        Aceita tanto DataFrames brutos CVM (CD_CONTA/DS_CONTA/VL_CONTA) quanto
        DataFrames normalizados pelo DFPParser (account_code/account_name/value).
        """
        if df is None or df.empty:
            return {}

        result: dict[str, float] = {}
        df = df.copy()

        # Detectar formato: normalizado (DFPParser) vs bruto (CVM)
        if "account_code" in df.columns:
            code_col, desc_col, val_col = "account_code", "account_name", "value"
        elif "CD_CONTA" in df.columns:
            code_col, desc_col, val_col = "CD_CONTA", "DS_CONTA", "VL_CONTA"
        else:
            return {}

        df[code_col] = df[code_col].astype(str).str.strip()
        if desc_col in df.columns:
            df[desc_col] = df[desc_col].astype(str).str.strip()
        else:
            df[desc_col] = ""
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        # Campos onde o nome da conta é mais confiável que o código (layout varia entre bancos)
        NAME_PRIORITY_FIELDS = {
            "total_equity",
            "shareholders_equity_direct",
            "minority_interest_bs",
            "total_liabilities_and_equity",
            "deposits",
            "funding_at_cost",
        }

        # Para cada linha, tentar mapear
        for _, row in df.iterrows():
            code = row[code_col]
            desc = row[desc_col]
            val = row[val_col]

            if pd.isna(val):
                continue

            field_by_name = self._map_name(desc)
            field_by_code = self._map_code(code)

            # Para campos ambíguos (equity, deposits), nome tem prioridade sobre código
            if field_by_name and field_by_name in NAME_PRIORITY_FIELDS:
                field = field_by_name
            else:
                field = field_by_code or field_by_name

            if field and field not in result:
                result[field] = float(val)

        return result

    def _map_code(self, code: str) -> str | None:
        """Mapeamento exato por código."""
        return BANK_ACCOUNT_MAP.get(code)

    def _map_name(self, desc: str) -> str | None:
        """Fallback por regex no nome da conta."""
        for pattern, field in BANK_NAME_PATTERNS:
            if pattern.search(desc):
                return field
        return None
