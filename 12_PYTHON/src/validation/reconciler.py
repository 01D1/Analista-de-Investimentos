"""
reconciler.py
-------------
Executa os checks de reconciliação contábil definidos em
13_VALIDATION/CHECKLIST_RECONCILIACAO.md e as REGRAS_DE_ALERTA.

Valida:
  1. Equação fundamental: Ativo = Passivo + PL
  2. Caixa DFC = Caixa BP
  3. Variação de caixa DFC coerente
  4. EBITDA calculado vs informado
  5. Dívida líquida coerente
  6. Alertas de valuation (quando aplicável)

Uso:
    from validation.reconciler import Reconciler
    from validation.schemas import FinancialStatements

    rec = Reconciler()
    report = rec.run(statements)
    rec.print_report(report)
    assert report["blocking_errors"] == 0, "Reconciliação com erros críticos"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from validation.schemas import FinancialStatements

logger = logging.getLogger(__name__)

TOLERANCE = 1.0  # R$ mil — diferença aceitável por arredondamento


# ---------------------------------------------------------------------------
# Resultado de um check individual
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str  # "critical" | "warning" | "info"
    message: str
    detail: str | None = None

    @property
    def emoji(self) -> str:
        if self.passed:
            return "[OK]"
        return "[ERRO]" if self.severity == "critical" else "[AVISO]"


# ---------------------------------------------------------------------------
# Relatório completo
# ---------------------------------------------------------------------------


@dataclass
class ReconciliationReport:
    ticker: str
    period: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def blocking_errors(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "critical")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "warning")

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    def summary(self) -> str:
        total = len(self.checks)
        return (
            f"{self.ticker} {self.period}: "
            f"{self.passed_count}/{total} checks OK | "
            f"{self.blocking_errors} erros críticos | "
            f"{self.warnings} avisos"
        )


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------


class Reconciler:
    """Executa todos os checks de reconciliação sobre um FinancialStatements."""

    def run(self, stmts: FinancialStatements) -> ReconciliationReport:
        """
        Executa todos os checks e retorna o relatório.

        Args:
            stmts: Demonstrações financeiras validadas pelo schema Pydantic.

        Returns:
            ReconciliationReport com todos os resultados.
        """
        report = ReconciliationReport(
            ticker=stmts.metadata.ticker,
            period=stmts.metadata.period,
        )
        checks = [
            self._check_balance_equation(stmts),
            self._check_cash_dfc_vs_bp(stmts),
            self._check_cash_change_consistency(stmts),
            self._check_net_income_dre_vs_dfc(stmts),
            self._check_ebitda_consistency(stmts),
            self._check_net_debt(stmts),
            self._check_cfo_sign(stmts),
            self._check_capex_sign(stmts),
            self._check_effective_tax_rate(stmts),
            self._check_gross_profit_arithmetic(stmts),
        ]
        report.checks.extend(checks)

        if report.blocking_errors:
            logger.error(
                "[%s %s] %d erros críticos de reconciliação",
                stmts.metadata.ticker,
                stmts.metadata.period,
                report.blocking_errors,
            )
        elif report.warnings:
            logger.warning(
                "[%s %s] %d avisos de reconciliação",
                stmts.metadata.ticker,
                stmts.metadata.period,
                report.warnings,
            )
        else:
            logger.info("[%s %s] Reconciliação OK", stmts.metadata.ticker, stmts.metadata.period)

        return report

    def print_report(self, report: ReconciliationReport) -> None:
        """Imprime o relatório formatado no terminal."""
        print(f"\n{'=' * 60}")
        print(f"  RECONCILIAÇÃO: {report.ticker} | {report.period}")
        print(f"{'=' * 60}")
        for c in report.checks:
            status = c.emoji
            line = f"  {status:<8} {c.name}"
            if not c.passed:
                line += f"\n           >> {c.message}"
                if c.detail:
                    line += f"\n              {c.detail}"
            print(line)
        print(f"\n  {report.summary()}")
        print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # Checks individuais
    # ------------------------------------------------------------------

    def _check_balance_equation(self, s: FinancialStatements) -> CheckResult:
        """Ativo Total = Passivo Total + PL"""
        diff = s.balance_sheet.balance_difference or 0.0
        passed = abs(diff) <= TOLERANCE
        return CheckResult(
            name="Equação fundamental (Ativo = Passivo + PL)",
            passed=passed,
            severity="critical",
            message=f"Diferença de R$ {diff:,.0f} mil — verificar extração",
            detail=f"Ativo: {s.balance_sheet.assets.total_assets:,.0f} | "
            f"Passivo+PL: {s.balance_sheet.liabilities.total_liabilities_and_equity:,.0f}",
        )

    def _check_cash_dfc_vs_bp(self, s: FinancialStatements) -> CheckResult:
        """Caixa final da DFC deve ser igual ao caixa no BP."""
        dfc_cash = s.cash_flow.ending_cash
        bp_cash = s.balance_sheet.assets.cash
        diff = abs(dfc_cash - bp_cash)
        passed = diff <= TOLERANCE
        return CheckResult(
            name="Caixa DFC = Caixa BP",
            passed=passed,
            severity="critical",
            message=f"DFC: {dfc_cash:,.0f} | BP: {bp_cash:,.0f} | Dif: {diff:,.0f}",
        )

    def _check_cash_change_consistency(self, s: FinancialStatements) -> CheckResult:
        """Variação DFC deve bater com caixa final − caixa inicial."""
        passed = s.cash_flow.cash_check is True
        change = s.cash_flow.net_cash_change or 0
        expected = s.cash_flow.ending_cash - s.cash_flow.beginning_cash
        diff = abs(change - expected)
        return CheckResult(
            name="Variação de caixa DFC consistente",
            passed=passed,
            severity="critical",
            message=f"CFO+CFI+CFF={change:,.0f} vs Final-Inicial={expected:,.0f} | Dif={diff:,.0f}",
        )

    def _check_net_income_dre_vs_dfc(self, s: FinancialStatements) -> CheckResult:
        """Lucro líquido da DRE deve ser ponto de partida do CFO (método indireto)."""
        ll_dre = s.income_statement.net_income
        ll_dfc = s.cash_flow.net_income_cfo
        if ll_dfc is None:
            return CheckResult(
                name="Lucro DRE = ponto de partida DFC",
                passed=True,
                severity="info",
                message="Campo net_income_cfo não preenchido — verificação pulada.",
            )
        diff = abs(ll_dre - ll_dfc)
        passed = (
            diff <= TOLERANCE * 10
        )  # tolerância maior por diferença entre controladora/consolidado
        return CheckResult(
            name="Lucro DRE = ponto de partida DFC",
            passed=passed,
            severity="warning",
            message=f"DRE: {ll_dre:,.0f} | DFC: {ll_dfc:,.0f} | Dif: {diff:,.0f}",
            detail="Diferença pode ser normal se DRE é consolidado e DFC começa pelo lucro do controlador",
        )

    def _check_ebitda_consistency(self, s: FinancialStatements) -> CheckResult:
        """EBITDA calculado (EBIT + D&A) deve aproximar o EBITDA informado."""
        i = s.income_statement
        if i.ebit is None or i.depreciation_amortization is None or i.ebitda is None:
            return CheckResult(
                name="EBITDA calculado vs informado",
                passed=True,
                severity="info",
                message="Dados insuficientes para verificar — pulado.",
            )
        calc = i.ebit + i.depreciation_amortization
        diff = abs(calc - i.ebitda)
        pct = diff / abs(i.ebitda) if i.ebitda != 0 else 0
        passed = pct <= 0.05  # tolerância de 5%
        return CheckResult(
            name="EBITDA calculado vs informado",
            passed=passed,
            severity="warning",
            message=f"Calculado: {calc:,.0f} | Schema: {i.ebitda:,.0f} | Dif: {pct:.1%}",
            detail="Diferença > 5% pode indicar ajustes não mapeados",
        )

    def _check_net_debt(self, s: FinancialStatements) -> CheckResult:
        """Dívida líquida deve ser coerente (não muito acima do razoável)."""
        nd = s.balance_sheet.net_debt
        ebitda = s.income_statement.ebitda
        if nd is None or ebitda is None or ebitda == 0:
            return CheckResult(
                name="Nível de dívida líquida / EBITDA",
                passed=True,
                severity="info",
                message="Dados insuficientes — pulado.",
            )
        ratio = nd / ebitda
        passed = ratio <= 5.0
        return CheckResult(
            name="Nível de dívida líquida / EBITDA",
            passed=passed,
            severity="warning",
            message=f"Dív. Líq./EBITDA = {ratio:.1f}x (alerta se > 5x para não-financeiras)",
            detail=f"Dív. Líq.: {nd:,.0f} | EBITDA: {ebitda:,.0f}",
        )

    def _check_cfo_sign(self, s: FinancialStatements) -> CheckResult:
        """CFO deve ser positivo para empresas operacionalmente saudáveis."""
        cfo = s.cash_flow.cfo
        passed = cfo > 0
        return CheckResult(
            name="CFO positivo",
            passed=passed,
            severity="warning",
            message=f"CFO = {cfo:,.0f} — CFO negativo pode indicar problemas operacionais",
        )

    def _check_capex_sign(self, s: FinancialStatements) -> CheckResult:
        """Capex deve ser negativo (saída de caixa)."""
        capex = s.cash_flow.capex
        if capex is None:
            return CheckResult(
                name="Sinal do Capex",
                passed=True,
                severity="info",
                message="Capex não informado — pulado.",
            )
        passed = capex <= 0
        return CheckResult(
            name="Sinal do Capex (deve ser negativo)",
            passed=passed,
            severity="warning",
            message=f"Capex = {capex:,.0f} — verificar sinal se positivo",
        )

    def _check_effective_tax_rate(self, s: FinancialStatements) -> CheckResult:
        """Alíquota efetiva de IR deve estar entre 10% e 45%."""
        i = s.income_statement
        if i.ebt is None or i.income_tax is None or i.ebt == 0:
            return CheckResult(
                name="Alíquota efetiva de IR",
                passed=True,
                severity="info",
                message="Dados insuficientes — pulado.",
            )
        eff_rate = abs(i.income_tax) / abs(i.ebt)
        passed = 0.05 <= eff_rate <= 0.50
        return CheckResult(
            name="Alíquota efetiva de IR (5%–50%)",
            passed=passed,
            severity="warning",
            message=f"Alíquota efetiva: {eff_rate:.1%} — fora do range normal",
            detail="Verificar créditos fiscais, incentivos ou evento especial",
        )

    def _check_gross_profit_arithmetic(self, s: FinancialStatements) -> CheckResult:
        """Lucro Bruto = Receita Líquida + CPV (CPV é negativo)."""
        i = s.income_statement
        if i.gross_profit is None or i.cogs is None:
            return CheckResult(
                name="Lucro Bruto = Rec. Líq. + CPV",
                passed=True,
                severity="info",
                message="Dados insuficientes — pulado.",
            )
        calc = i.net_revenue + i.cogs  # cogs é negativo
        diff = abs(calc - i.gross_profit)
        passed = diff <= TOLERANCE
        return CheckResult(
            name="Lucro Bruto = Rec. Líq. + CPV",
            passed=passed,
            severity="critical",
            message=f"Calculado: {calc:,.0f} | Informado: {i.gross_profit:,.0f} | Dif: {diff:,.0f}",
        )
