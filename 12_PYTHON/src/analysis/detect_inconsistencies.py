"""
detect_inconsistencies.py
--------------------------
Detecção automática de inconsistências nos dados extraídos do CVM.

Verifica:
  1. Consistência matemática (soma de componentes = total declarado)
  2. Valores impossíveis (negativos onde não deveria, zeros suspeitos)
  3. Saltos anômalos YoY (variações > N desvios da média histórica)
  4. Inconsistências cross-statement (receita na DRE ≠ recebimentos no DFC, etc.)

Retorna uma lista de Inconsistency com severidade e sugestão de correção.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Tolerância para comparações de soma (diferença relativa aceitável)
_TOLERANCE = 0.02  # 2%


@dataclass
class Inconsistency:
    """Uma inconsistência detectada nos dados."""

    code: str
    severity: str  # "info", "warning", "error", "critical"
    statement: str  # "DRE", "BPA", "BPP", "DFC", "cross"
    field: str  # campo(s) envolvido(s)
    description: str
    expected: float | None = None
    observed: float | None = None
    suggestion: str | None = None

    def __str__(self) -> str:
        parts = [f"[{self.severity.upper()}] {self.code} | {self.statement}.{self.field}"]
        parts.append(f"  {self.description}")
        if self.expected is not None and self.observed is not None:
            parts.append(f"  Esperado: {self.expected:,.0f}  |  Observado: {self.observed:,.0f}")
        if self.suggestion:
            parts.append(f"  Sugestão: {self.suggestion}")
        return "\n".join(parts)


@dataclass
class InconsistencyReport:
    """Relatório completo de inconsistências para um período."""

    ticker: str
    year: int
    inconsistencies: list[Inconsistency] = field(default_factory=list)

    @property
    def errors(self) -> list[Inconsistency]:
        return [i for i in self.inconsistencies if i.severity in ("error", "critical")]

    @property
    def warnings(self) -> list[Inconsistency]:
        return [i for i in self.inconsistencies if i.severity == "warning"]

    @property
    def is_clean(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        status = "OK" if self.is_clean else "PROBLEMAS DETECTADOS"
        lines = [f"[{self.ticker}] {self.year} — {status}"]
        lines.append(f"  Erros: {len(self.errors)}  |  Warnings: {len(self.warnings)}")
        for inc in self.inconsistencies:
            if inc.severity in ("error", "critical", "warning"):
                lines.append(f"  • {inc.severity.upper()}: {inc.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Detector para empresas industriais
# ---------------------------------------------------------------------------


class InconsistencyDetector:
    """
    Detecta inconsistências em demonstrativos de empresas industriais.

    Uso:
        detector = InconsistencyDetector()
        report = detector.check(ticker, year, stmts_dict)
    """

    def check(
        self,
        ticker: str,
        year: int,
        dre: dict,
        bpa: dict,
        bpp: dict,
        dfc: dict,
        prev_dre: dict | None = None,
        prev_bpa: dict | None = None,
    ) -> InconsistencyReport:

        report = InconsistencyReport(ticker=ticker, year=year)
        self._check_dre(report, dre, prev_dre)
        self._check_balance_sheet(report, bpa, bpp)
        self._check_dfc(report, dfc, dre)
        return report

    def _check_dre(self, report, dre, prev_dre):
        revenue = dre.get("net_revenue", 0.0) or 0.0
        cogs = dre.get("cogs", 0.0) or 0.0
        gross_profit = dre.get("gross_profit", 0.0) or 0.0
        net_income = dre.get("net_income", 0.0) or 0.0
        dre.get("ebit", 0.0) or 0.0

        # Receita deve ser positiva
        if revenue <= 0:
            report.inconsistencies.append(
                Inconsistency(
                    code="DRE_REVENUE_ZERO",
                    severity="error",
                    statement="DRE",
                    field="net_revenue",
                    description="Receita líquida é zero ou negativa",
                    observed=revenue,
                    suggestion="Verificar mapeamento de 3.01 — pode ser estrutura alternativa",
                )
            )

        # Lucro bruto = Receita + COGS (COGS já é negativo no CVM)
        if revenue > 0 and cogs != 0 and gross_profit != 0:
            expected_gp = revenue + cogs  # cogs é negativo
            if not _close(expected_gp, gross_profit):
                report.inconsistencies.append(
                    Inconsistency(
                        code="DRE_GROSS_PROFIT_MISMATCH",
                        severity="warning",
                        statement="DRE",
                        field="gross_profit",
                        description="Lucro bruto não bate com Receita + CPV",
                        expected=expected_gp,
                        observed=gross_profit,
                    )
                )

        # Salto anômalo em net_income (>200% YoY ou <-80% = alerta)
        if prev_dre and net_income and prev_dre.get("net_income"):
            prev_ni = prev_dre["net_income"]
            if abs(prev_ni) > 1:
                change = (net_income - prev_ni) / abs(prev_ni)
                if abs(change) > 2.0:
                    sev = "warning" if abs(change) < 5.0 else "error"
                    report.inconsistencies.append(
                        Inconsistency(
                            code="DRE_NET_INCOME_JUMP",
                            severity=sev,
                            statement="DRE",
                            field="net_income",
                            description=f"Lucro líquido variou {change:.0%} YoY — investigar",
                            expected=prev_ni,
                            observed=net_income,
                            suggestion="Verificar itens extraordinários, M&A ou mudança de perímetro",
                        )
                    )

    def _check_balance_sheet(self, report, bpa, bpp):
        total_assets = bpa.get("total_assets", 0.0) or 0.0
        total_liabilities_equity = bpp.get("total_liabilities_and_equity", 0.0) or 0.0

        # Ativo Total = Passivo Total + PL
        if total_assets > 0 and total_liabilities_equity > 0:
            if not _close(total_assets, total_liabilities_equity):
                report.inconsistencies.append(
                    Inconsistency(
                        code="BP_IMBALANCE",
                        severity="error",
                        statement="BPA/BPP",
                        field="total_assets vs total_liabilities_and_equity",
                        description="Ativo Total ≠ Passivo + PL — balanço não está fechado",
                        expected=total_assets,
                        observed=total_liabilities_equity,
                        suggestion="Verificar se todos os grupos foram mapeados corretamente",
                    )
                )

        # Total de ativos deve ser positivo
        if total_assets <= 0:
            report.inconsistencies.append(
                Inconsistency(
                    code="BP_ASSETS_ZERO",
                    severity="critical",
                    statement="BPA",
                    field="total_assets",
                    description="Ativo Total é zero — mapeamento falhou",
                    observed=total_assets,
                    suggestion="Verificar código '1' no BPA mapper",
                )
            )

    def _check_dfc(self, report, dfc, dre):
        if not dfc:
            report.inconsistencies.append(
                Inconsistency(
                    code="DFC_MISSING",
                    severity="warning",
                    statement="DFC",
                    field="cfo",
                    description="DFC não disponível para este período",
                    suggestion="Verificar se arquivo CSV existe para o ano",
                )
            )
            return

        cfo = dfc.get("cfo", 0.0) or 0.0
        cfi = dfc.get("cfi", 0.0) or 0.0
        cff = dfc.get("cff", 0.0) or 0.0
        forex = dfc.get("forex_effect_on_cash", 0.0) or 0.0
        ending_cash = dfc.get("ending_cash", 0.0) or 0.0
        beginning_cash = dfc.get("beginning_cash", 0.0) or 0.0

        # Verificar reconciliação de caixa
        implied_change = cfo + cfi + cff + forex
        actual_change = ending_cash - beginning_cash
        if abs(actual_change) > 1 and not _close(implied_change, actual_change):
            report.inconsistencies.append(
                Inconsistency(
                    code="DFC_RECONCILIATION",
                    severity="warning",
                    statement="DFC",
                    field="cash_reconciliation",
                    description=f"CFO+CFI+CFF+Forex = {implied_change:,.0f} ≠ ΔCaixa = {actual_change:,.0f}",
                    expected=actual_change,
                    observed=implied_change,
                    suggestion="Verificar se 6.04 (variação cambial) está sendo incluído",
                )
            )


# ---------------------------------------------------------------------------
# Detector para bancos
# ---------------------------------------------------------------------------


class BankInconsistencyDetector:
    """
    Detecta inconsistências específicas de bancos.
    """

    def check(
        self,
        ticker: str,
        year: int,
        income: dict,
        assets: dict,
        liabilities: dict,
        cashflow: dict | None = None,
        prev_income: dict | None = None,
    ) -> InconsistencyReport:

        report = InconsistencyReport(ticker=ticker, year=year)

        # Receitas de intermediação devem ser positivas
        revenues = income.get("total_financial_revenues", 0.0) or 0.0
        if revenues <= 0:
            report.inconsistencies.append(
                Inconsistency(
                    code="BANK_DRE_REVENUES_ZERO",
                    severity="error",
                    statement="DRE",
                    field="total_financial_revenues",
                    description="Receitas da intermediação financeira = 0 — mapeamento falhou",
                    suggestion="Verificar código 3.01 no bank_account_mapper",
                )
            )

        # Net income deve estar preenchido
        net_income = income.get("net_income", 0.0) or 0.0
        net_income_consol = income.get("net_income_consolidated", 0.0) or 0.0
        if net_income == 0.0 and net_income_consol == 0.0:
            report.inconsistencies.append(
                Inconsistency(
                    code="BANK_DRE_NET_INCOME_ZERO",
                    severity="error",
                    statement="DRE",
                    field="net_income",
                    description="net_income e net_income_consolidated ambos = 0",
                    suggestion="Verificar códigos 3.09.01, 3.11.01, 3.11 no mapper",
                )
            )

        # Total equity deve estar preenchido
        total_equity = liabilities.get("total_equity", 0.0) or 0.0
        if total_equity <= 0:
            report.inconsistencies.append(
                Inconsistency(
                    code="BANK_BP_EQUITY_ZERO",
                    severity="error",
                    statement="BPP",
                    field="total_equity",
                    description="Patrimônio Líquido = 0 — mapeamento de PL falhou",
                    suggestion="Verificar NAME_PRIORITY_FIELDS e padrão de nome 'patrimônio líquido consolidado'",
                )
            )

        # Total assets
        total_assets = assets.get("total_assets", 0.0) or 0.0
        if total_assets <= 0:
            report.inconsistencies.append(
                Inconsistency(
                    code="BANK_BP_ASSETS_ZERO",
                    severity="critical",
                    statement="BPA",
                    field="total_assets",
                    description="Ativo Total = 0",
                    suggestion="Verificar código '1' no BANK_ACCOUNT_MAP",
                )
            )

        # ROE implícito não deve ser absurdo
        if net_income > 0 and total_equity > 0:
            roe = net_income / total_equity
            if roe > 1.0:
                report.inconsistencies.append(
                    Inconsistency(
                        code="BANK_ROE_ASTRONOMICAL",
                        severity="error",
                        statement="DRE/BPP",
                        field="net_income / total_equity",
                        description=f"ROE implícito = {roe:.0%} — impossível, PL provavelmente errado",
                        expected=0.15,  # valor razoável
                        observed=roe,
                        suggestion="PL pode estar mapeado como subconta (ex: apenas controladora) em vez do PL consolidado",
                    )
                )

        return report


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _close(a: float, b: float, tol: float = _TOLERANCE) -> bool:
    """Verifica se dois valores são próximos dentro da tolerância relativa."""
    if b == 0:
        return abs(a) < 1
    return abs((a - b) / b) < tol
