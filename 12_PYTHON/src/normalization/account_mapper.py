"""
account_mapper.py
-----------------
Normaliza contas financeiras brutas (vindas da CVM ou de outras fontes)
para o schema padronizado do projeto.

Problema que resolve:
  Cada empresa pode nomear a mesma conta de forma diferente.
  Ex: "Receita de Vendas e/ou Serviços" vs "Receita Líquida" vs "3.03"
  O mapeamento aqui garante que tudo converge para o mesmo campo.

Estratégias de mapeamento (em ordem de prioridade):
  1. Código de conta exato (mais confiável — ex: "3.03")
  2. Código de conta por prefixo
  3. Nome de conta por regex

Uso:
    from normalization.account_mapper import AccountMapper

    mapper = AccountMapper()
    normalized = mapper.map_df(df)  # adiciona coluna "normalized_name"
    d = mapper.to_dict(df)          # {campo: valor}
"""

from __future__ import annotations

import logging
import re

import pandas as pd

from parsers.dfp_parser import ACCOUNT_MAP as CODE_MAP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento por código CVM (importado do parser)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Mapeamento por regex de nome (fallback para fontes não-CVM)
# ---------------------------------------------------------------------------

NAME_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Receita
    (re.compile(r"receita\s+l[ií]quida", re.I), "net_revenue"),
    (re.compile(r"receita\s+bruta", re.I), "gross_revenue"),
    (re.compile(r"dedu[çc][ãa]o|abatimento|devolu", re.I), "revenue_deductions"),
    # Resultado bruto
    (re.compile(r"custo\s+(dos?\s+)?produtos?|cpv|cogs|custo\s+das?\s+vendas", re.I), "cogs"),
    (re.compile(r"lucro\s+bruto", re.I), "gross_profit"),
    # Despesas
    (re.compile(r"despesas?\s+com\s+vendas", re.I), "selling_expenses"),
    (
        re.compile(r"despesas?\s+gerais|g&a|sg&a|despesas?\s+administrativas", re.I),
        "general_admin_expenses",
    ),
    (re.compile(r"equivalência\s+patrimonial", re.I), "equity_income"),
    (re.compile(r"deprecia[çc][ãa]o|amortiza[çc][ãa]o|d&a", re.I), "depreciation_amortization"),
    # Resultado operacional
    (re.compile(r"\bebit\b|resultado\s+operacional\s+antes", re.I), "ebit"),
    (re.compile(r"\bebitda\b", re.I), "ebitda"),
    # Financeiro
    (re.compile(r"receita\s+financeira", re.I), "financial_income"),
    (re.compile(r"despesa\s+financeira|custo\s+financeiro", re.I), "financial_expenses"),
    (re.compile(r"resultado\s+financeiro\s+(l[ií]quido)?", re.I), "net_financial_result"),
    # Resultado líquido
    (re.compile(r"lucro\s+antes\s+do\s+imposto|ebt|lair", re.I), "ebt"),
    (re.compile(r"imposto\s+de\s+renda|irpj|csll|ir\s*/\s*cs", re.I), "income_tax"),
    (re.compile(r"lucro\s+l[ií]quido\s+consolidado", re.I), "net_income_consolidated"),
    (
        re.compile(r"participação\s+de\s+minoritário|nci|interesse\s+de\s+não", re.I),
        "minority_interest",
    ),
    (re.compile(r"lucro\s+l[ií]quido", re.I), "net_income"),
    # BP — Ativo
    (re.compile(r"caixa\s+e\s+equivalentes", re.I), "cash"),
    (re.compile(r"aplica[çc][õo]es\s+financeiras.*curto", re.I), "short_term_investments"),
    (re.compile(r"contas?\s+a\s+receber", re.I), "accounts_receivable"),
    (re.compile(r"estoques?", re.I), "inventories"),
    (re.compile(r"imobilizado", re.I), "ppe_net"),
    (re.compile(r"intang[íi]vel", re.I), "intangibles_net"),
    # BP — Passivo
    (re.compile(r"fornecedores", re.I), "suppliers"),
    (re.compile(r"d[ií]vida.*curto\s+prazo|empr[ée]stimos.*cp", re.I), "short_term_debt"),
    (re.compile(r"d[ií]vida.*longo\s+prazo|empr[ée]stimos.*lp|debenture", re.I), "long_term_debt"),
    (re.compile(r"patrim[ôo]nio\s+l[ií]quido", re.I), "shareholders_equity"),
    # DFC
    (re.compile(r"caixa\s+(gerado|l[ií]quido)\s+(pelas?\s+)?opera[çc][õo]es|cfo", re.I), "cfo"),
    (
        re.compile(r"capex|ativo\s+imobilizado|ativo\s+intang|aquisi[çc][ãa]o\s+de\s+ativo", re.I),
        "capex",
    ),
    (re.compile(r"caixa.*atividades\s+de\s+investimento|cfi", re.I), "cfi"),
    (re.compile(r"caixa.*atividades\s+de\s+financiamento|cff", re.I), "cff"),
    (re.compile(r"dividendos\s+pagos", re.I), "dividends_paid"),
]


# ---------------------------------------------------------------------------
# AccountMapper
# ---------------------------------------------------------------------------


class AccountMapper:
    """
    Mapeia contas brutas para o schema padronizado.

    Prioridade:
      1. Código exato (CD_CONTA)
      2. Prefixo de código
      3. Regex no nome da conta
    """

    def map_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adiciona coluna 'normalized_name' ao DataFrame.
        Funciona com DataFrames vindos do DFPParser ou de outras fontes.

        Args:
            df: DataFrame com colunas 'account_code' e/ou 'account_name'

        Returns:
            DataFrame original com coluna 'normalized_name' adicionada/atualizada
        """
        df = df.copy()
        df["normalized_name"] = df.apply(self._map_row, axis=1)
        return df

    def to_dict(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Converte um DataFrame mapeado em {campo_schema: valor}.
        Quando há múltiplas linhas para o mesmo campo, mantém a de maior nível (menos específica).

        Returns:
            Dicionário pronto para alimentar os schemas Pydantic.
        """
        df = self.map_df(df)
        result: dict[str, float] = {}
        for _, row in df.iterrows():
            norm = row.get("normalized_name")
            value = row.get("value")
            if norm and value is not None and norm not in result:
                try:
                    result[norm] = float(value)
                except (ValueError, TypeError):
                    pass
        return result

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _map_row(self, row: pd.Series) -> str | None:
        """Aplica as estratégias de mapeamento para uma linha."""
        code = str(row.get("account_code", "")).strip()
        name = str(row.get("account_name", "")).strip()

        # 1. Código exato
        if code in CODE_MAP:
            return CODE_MAP[code]

        # 2. Prefixo de código (ex: "3.03.01" → "3.03" → "net_revenue")
        for prefix, field_name in sorted(CODE_MAP.items(), key=lambda x: -len(x[0])):
            if code.startswith(prefix + "."):
                return field_name

        # 3. Regex no nome
        for pattern, field_name in NAME_PATTERNS:
            if pattern.search(name):
                return field_name

        return None
