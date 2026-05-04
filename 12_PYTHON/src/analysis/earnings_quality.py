"""
earnings_quality.py
--------------------
Módulo de avaliação de qualidade dos lucros.

Detecta discrepâncias entre lucro contábil e geração de caixa, accruals
elevados, e outros sinais de possível gerenciamento de resultados.

Funciona tanto para empresas industriais (FinancialStatements) quanto para
bancos (BankStatements).

Referências metodológicas:
  - Sloan (1996): componente accrual do lucro reverte no longo prazo
  - Dechow & Dichev (2002): qualidade de accruals vs. fluxo de caixa
  - Penman & Zhang (2002): hidden reserves e qualidade de lucros
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Score e flags de qualidade
# ---------------------------------------------------------------------------


@dataclass
class EarningsQualityFlag:
    """Um sinal específico de qualidade de lucro."""

    code: str  # ex: "ACCRUAL_HIGH"
    severity: str  # "low", "medium", "high", "critical"
    description: str  # o que foi detectado
    value: float | None = None  # o valor da métrica que triggou o flag
    threshold: float | None = None  # o threshold que foi ultrapassado


@dataclass
class EarningsQualityReport:
    """Resultado completo da avaliação de qualidade de lucros para um período."""

    ticker: str
    year: int

    # Métricas calculadas
    cfo_to_net_income: float | None = None  # CFO / Lucro Líquido
    accrual_ratio: float | None = None  # (Lucro − CFO) / Total Assets
    receivables_growth_vs_revenue: float | None = None  # % crescimento recebíveis vs receita
    capex_to_depreciation: float | None = None  # Capex / Depreciação
    gross_margin_stability: float | None = None  # desvio da margem bruta vs. média 3 anos
    net_margin_stability: float | None = None

    # Para bancos
    pdd_to_npl_ratio: float | None = None  # Cobertura de PDD
    loan_growth_vs_pdd_growth: float | None = None

    # Flags detectados
    flags: list[EarningsQualityFlag] = field(default_factory=list)

    # Score final (0–10, sendo 10 = máxima qualidade)
    score: float = 0.0

    @property
    def risk_level(self) -> str:
        if self.score >= 8.0:
            return "Baixo"
        elif self.score >= 6.0:
            return "Médio"
        elif self.score >= 4.0:
            return "Alto"
        else:
            return "Crítico"

    @property
    def critical_flags(self) -> list[EarningsQualityFlag]:
        return [f for f in self.flags if f.severity == "critical"]

    @property
    def high_flags(self) -> list[EarningsQualityFlag]:
        return [f for f in self.flags if f.severity == "high"]

    def summary(self) -> str:
        lines = [
            f"[{self.ticker}] {self.year} — Score: {self.score:.1f}/10 ({self.risk_level})",
        ]
        if self.cfo_to_net_income is not None:
            lines.append(f"  CFO/Lucro: {self.cfo_to_net_income:.1%}")
        if self.accrual_ratio is not None:
            lines.append(f"  Accrual ratio: {self.accrual_ratio:.1%}")
        for flag in self.flags:
            prefix = "⚠" if flag.severity in ("high", "critical") else "·"
            lines.append(f"  {prefix} [{flag.severity.upper()}] {flag.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Avaliador de qualidade industrial
# ---------------------------------------------------------------------------


class EarningsQualityAnalyzer:
    """
    Avalia qualidade dos lucros para empresas industriais.

    Uso:
        analyzer = EarningsQualityAnalyzer()
        report = analyzer.analyze(ticker, year, stmts, prev_stmts)
    """

    # Thresholds
    CFO_TO_NI_MIN = 0.70  # CFO deve ser ≥ 70% do lucro líquido
    ACCRUAL_RATIO_MAX = 0.08  # accruals > 8% dos ativos é sinal de alerta
    ACCRUAL_RATIO_CRITICAL = 0.15  # > 15% é crítico
    RECV_GROWTH_PREMIUM_MAX = 0.10  # recebíveis crescendo >10pp acima da receita
    CAPEX_TO_DEPR_HEALTHY = (0.8, 3.0)  # capex/depr fora de 0.8–3.0x é sinal

    def analyze(
        self,
        ticker: str,
        year: int,
        net_income: float,
        cfo: float,
        total_assets: float,
        revenue: float | None = None,
        receivables: float | None = None,
        capex: float | None = None,
        depreciation: float | None = None,
        gross_margin: float | None = None,
        # período anterior (para comparações YoY)
        prev_revenue: float | None = None,
        prev_receivables: float | None = None,
        prev_gross_margin: float | None = None,
    ) -> EarningsQualityReport:

        report = EarningsQualityReport(ticker=ticker, year=year)
        score = 10.0

        # 1. CFO / Lucro Líquido
        if net_income and abs(net_income) > 1:
            ratio = cfo / net_income
            report.cfo_to_net_income = ratio
            if ratio < self.CFO_TO_NI_MIN:
                sev = "critical" if ratio < 0.3 else ("high" if ratio < 0.5 else "medium")
                report.flags.append(
                    EarningsQualityFlag(
                        code="CFO_LOW",
                        severity=sev,
                        description=f"CFO/Lucro = {ratio:.1%} — conversão de caixa abaixo do mínimo ({self.CFO_TO_NI_MIN:.0%})",
                        value=ratio,
                        threshold=self.CFO_TO_NI_MIN,
                    )
                )
                score -= {"critical": 3.0, "high": 2.0, "medium": 1.0}[sev]

        # 2. Accrual ratio: (Lucro Líquido − CFO) / Total Assets
        if total_assets and abs(total_assets) > 1:
            accrual = (net_income - cfo) / total_assets
            report.accrual_ratio = accrual
            if abs(accrual) > self.ACCRUAL_RATIO_CRITICAL:
                report.flags.append(
                    EarningsQualityFlag(
                        code="ACCRUAL_CRITICAL",
                        severity="critical",
                        description=f"Accrual ratio = {accrual:.1%} — muito alto (threshold: {self.ACCRUAL_RATIO_CRITICAL:.0%})",
                        value=accrual,
                        threshold=self.ACCRUAL_RATIO_CRITICAL,
                    )
                )
                score -= 3.0
            elif abs(accrual) > self.ACCRUAL_RATIO_MAX:
                report.flags.append(
                    EarningsQualityFlag(
                        code="ACCRUAL_HIGH",
                        severity="high",
                        description=f"Accrual ratio = {accrual:.1%} — elevado (threshold: {self.ACCRUAL_RATIO_MAX:.0%})",
                        value=accrual,
                        threshold=self.ACCRUAL_RATIO_MAX,
                    )
                )
                score -= 1.5

        # 3. Crescimento de recebíveis vs. receita
        if (
            revenue
            and prev_revenue
            and receivables
            and prev_receivables
            and revenue > 0
            and prev_receivables > 0
        ):
            rev_growth = (revenue / prev_revenue) - 1
            recv_growth = (receivables / prev_receivables) - 1
            premium = recv_growth - rev_growth
            report.receivables_growth_vs_revenue = premium
            if premium > self.RECV_GROWTH_PREMIUM_MAX:
                sev = "high" if premium > 0.20 else "medium"
                report.flags.append(
                    EarningsQualityFlag(
                        code="RECEIVABLES_GROWTH",
                        severity=sev,
                        description=f"Recebíveis crescendo {premium:.1%} acima da receita — possível antecipação de receita",
                        value=premium,
                        threshold=self.RECV_GROWTH_PREMIUM_MAX,
                    )
                )
                score -= {"high": 2.0, "medium": 1.0}[sev]

        # 4. Capex / Depreciação
        if capex and depreciation and abs(depreciation) > 0:
            ratio = abs(capex) / abs(depreciation)
            report.capex_to_depreciation = ratio
            low, high = self.CAPEX_TO_DEPR_HEALTHY
            if ratio < low:
                report.flags.append(
                    EarningsQualityFlag(
                        code="CAPEX_BELOW_DEPR",
                        severity="medium",
                        description=f"Capex/Depreciação = {ratio:.1f}x — capex abaixo de manutenção (possível subinvestimento)",
                        value=ratio,
                        threshold=low,
                    )
                )
                score -= 0.5

        # 5. Margem bruta — estabilidade
        if gross_margin is not None and prev_gross_margin is not None:
            change = gross_margin - prev_gross_margin
            report.gross_margin_stability = change
            if change < -0.05:
                sev = "critical" if change < -0.10 else "high"
                report.flags.append(
                    EarningsQualityFlag(
                        code="MARGIN_DETERIORATION",
                        severity=sev,
                        description=f"Margem bruta caiu {change:.1%} vs. ano anterior",
                        value=change,
                    )
                )
                score -= {"critical": 1.5, "high": 0.5}[sev]

        report.score = max(0.0, min(10.0, score))
        return report


# ---------------------------------------------------------------------------
# Avaliador específico para bancos
# ---------------------------------------------------------------------------


class BankEarningsQualityAnalyzer:
    """
    Avalia qualidade dos lucros para bancos brasileiros.

    Foco em: adequação de provisões, qualidade da carteira de crédito,
    conversão CFO, e estabilidade de spreads.
    """

    PDD_COVERAGE_MIN = 0.80  # Cobertura de PDD / carteira vencida > 80%
    CFO_TO_NI_MIN = 0.60  # Bancos têm mais accruals por natureza — threshold menor

    def analyze(
        self,
        ticker: str,
        year: int,
        net_income: float,
        cfo: float,
        total_assets: float,
        loan_portfolio: float | None = None,
        loan_loss_provision: float | None = None,
        loan_loss_reserve: float | None = None,
        npl_estimate: float | None = None,  # inadimplência estimada
        # período anterior
        prev_loan_portfolio: float | None = None,
        prev_loan_loss_provision: float | None = None,
    ) -> EarningsQualityReport:

        report = EarningsQualityReport(ticker=ticker, year=year)
        score = 10.0

        # 1. CFO / Lucro (threshold menor para bancos)
        if net_income and abs(net_income) > 1:
            ratio = cfo / net_income
            report.cfo_to_net_income = ratio
            if ratio < self.CFO_TO_NI_MIN:
                sev = "high" if ratio < 0.3 else "medium"
                report.flags.append(
                    EarningsQualityFlag(
                        code="CFO_LOW_BANK",
                        severity=sev,
                        description=f"CFO/Lucro = {ratio:.1%} — baixo para banco (threshold: {self.CFO_TO_NI_MIN:.0%})",
                        value=ratio,
                        threshold=self.CFO_TO_NI_MIN,
                    )
                )
                score -= {"high": 2.0, "medium": 1.0}[sev]

        # 2. Crescimento de provisões vs. crescimento da carteira
        if (
            loan_portfolio
            and prev_loan_portfolio
            and loan_loss_provision
            and prev_loan_loss_provision
            and prev_loan_portfolio > 0
            and prev_loan_loss_provision > 0
        ):
            portfolio_growth = (loan_portfolio / prev_loan_portfolio) - 1
            pdd_growth = (abs(loan_loss_provision) / abs(prev_loan_loss_provision)) - 1
            diff = pdd_growth - portfolio_growth
            report.loan_growth_vs_pdd_growth = diff

            # Carteira crescendo muito mais rápido que provisões = risco de subalocação
            if portfolio_growth - pdd_growth > 0.15:
                report.flags.append(
                    EarningsQualityFlag(
                        code="PDD_BELOW_PORTFOLIO_GROWTH",
                        severity="high",
                        description=(
                            f"Carteira cresceu {portfolio_growth:.1%} mas PDD cresceu apenas "
                            f"{pdd_growth:.1%} — possível subprovisamento"
                        ),
                        value=portfolio_growth - pdd_growth,
                        threshold=0.15,
                    )
                )
                score -= 2.0

        # 3. Cobertura de PDD / inadimplência
        if loan_loss_reserve and npl_estimate and abs(npl_estimate) > 0:
            coverage = abs(loan_loss_reserve) / abs(npl_estimate)
            report.pdd_to_npl_ratio = coverage
            if coverage < self.PDD_COVERAGE_MIN:
                sev = "critical" if coverage < 0.60 else "high"
                report.flags.append(
                    EarningsQualityFlag(
                        code="LOW_PDD_COVERAGE",
                        severity=sev,
                        description=f"Cobertura de provisão = {coverage:.1%} — abaixo do mínimo saudável ({self.PDD_COVERAGE_MIN:.0%})",
                        value=coverage,
                        threshold=self.PDD_COVERAGE_MIN,
                    )
                )
                score -= {"critical": 3.0, "high": 1.5}[sev]

        report.score = max(0.0, min(10.0, score))
        return report
