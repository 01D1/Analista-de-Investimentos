"""
risk_engine.py
--------------
Detecta automaticamente riscos financeiros usando thresholds de config/sectors.yaml.

Cada setor tem seus próprios limites (nd_ebitda, leverage, margens, etc.).
As regras são aplicadas dinamicamente com base no SectorConfig do ticker.

Uso:
    from src.analysis.risk_engine import assess_risk

    report = assess_risk("BBAS3")
    report = assess_risk("WEGE3")
    print(report.summary())
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.utils.logger import get_logger
from src.valuation.sector_config import SectorConfig

log = get_logger(__name__)
Severity = str  # "low" | "medium" | "high" | "critical"
_SEV_ORDER = ["low", "medium", "high", "critical"]


@dataclass
class Risk:
    code: str
    severity: Severity
    category: str
    description: str
    detail: str = ""
    triggered_at: str = field(default_factory=lambda: str(date.today()))

    def __str__(self) -> str:
        labels = {"low": "INFO", "medium": "AVISO", "high": "RISCO", "critical": "CRÍTICO"}
        return f"[{labels.get(self.severity, '?')}] {self.code}: {self.description}"


@dataclass
class RiskReport:
    ticker: str
    sector_type: str = ""
    assessed_at: str = field(default_factory=lambda: str(date.today()))
    risks: list[Risk] = field(default_factory=list)
    overall_severity: Severity = "low"

    @property
    def is_clean(self) -> bool:
        return len(self.risks) == 0

    def summary(self) -> str:
        if self.is_clean:
            return f"[{self.ticker}] Nenhum risco identificado [{self.sector_type}]"
        lines = [
            f"[{self.ticker}] {len(self.risks)} risco(s) "
            f"— overall: {self.overall_severity.upper()} [{self.sector_type}]"
        ]
        for r in sorted(self.risks, key=lambda x: _SEV_ORDER.index(x.severity), reverse=True):
            lines.append(f"  {r}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "sector_type": self.sector_type,
            "assessed_at": self.assessed_at,
            "overall_severity": self.overall_severity,
            "risk_count": len(self.risks),
            "risks": [r.__dict__ for r in self.risks],
        }


# ── Engine ────────────────────────────────────────────────────────────────────


class RiskEngine:
    """
    Avalia riscos financeiros com base nas métricas e nos thresholds do setor.

    Os limites vêm de config/sectors.yaml → risk_thresholds por setor.
    """

    def __init__(self, output_dir: Path | None = None):
        from config.settings import settings

        self.output_dir = output_dir or settings.data_output

    def assess(self, ticker: str, force: bool = False) -> RiskReport:
        output_path = self.output_dir / ticker / "risk_report.json"
        if output_path.exists() and not force:
            try:
                data = json.loads(output_path.read_text())
                return RiskReport(
                    ticker=ticker,
                    sector_type=data.get("sector_type", ""),
                    assessed_at=data.get("assessed_at", str(date.today())),
                    risks=[Risk(**r) for r in data.get("risks", [])],
                    overall_severity=data.get("overall_severity", "low"),
                )
            except Exception:
                pass

        metrics = self._load_metrics(ticker)
        if not metrics:
            log.warning(f"[{ticker}] sem métricas — execute 'analyze' primeiro")
            return RiskReport(ticker=ticker)

        cfg = SectorConfig.for_ticker(ticker)
        thr = cfg.risk_thresholds
        report = RiskReport(ticker=ticker, sector_type=cfg.sector_type)

        # Roteamento por modelo financeiro
        if cfg.is_bank_model:
            self._check_bank(report, metrics, thr)
        else:
            self._check_industrial(report, metrics, cfg, thr)

        self._check_common(report, metrics, thr)
        report.overall_severity = _max_severity(report.risks)

        self._save(report, output_path)
        log.info(
            f"[{ticker}] risco: {report.overall_severity.upper()} "
            f"({len(report.risks)} alerta(s)) [{cfg.sector_type}]"
        )
        return report

    # ── Regras bancos ─────────────────────────────────────────────────────────

    def _check_bank(self, report: RiskReport, metrics: dict[int, dict], thr: dict) -> None:
        years = sorted(metrics.keys())
        last = metrics[years[-1]]

        roe = last.get("roe")
        if roe is not None:
            sev = None
            if roe < thr.get("roe_min_critical", 0.05):
                sev = "critical"
            elif roe < thr.get("roe_min_high", 0.10):
                sev = "high"
            elif roe < thr.get("roe_min_low", 0.12):
                sev = "medium"
            if sev:
                report.risks.append(
                    Risk(
                        code="BANK_LOW_ROE",
                        severity=sev,
                        category="profitability",
                        description=f"ROE baixo: {roe:.1%}",
                        detail=f"Threshold mínimo: {thr.get('roe_min_low', 0.12):.1%}",
                    )
                )

        leverage = last.get("leverage")
        if leverage is not None:
            if leverage > thr.get("leverage_max_critical", 20.0):
                sev = "critical"
            elif leverage > thr.get("leverage_max_high", 15.0):
                sev = "high"
            else:
                sev = None
            if sev:
                report.risks.append(
                    Risk(
                        code="BANK_HIGH_LEVERAGE",
                        severity=sev,
                        category="leverage",
                        description=f"Alavancagem elevada: {leverage:.1f}x Ativos/PL",
                    )
                )

        eff = last.get("efficiency_ratio")
        if eff is not None:
            if eff > thr.get("efficiency_max_high", 0.70):
                sev = "high"
            elif eff > thr.get("efficiency_max_medium", 0.60):
                sev = "medium"
            else:
                sev = None
            if sev:
                report.risks.append(
                    Risk(
                        code="BANK_HIGH_EFFICIENCY_RATIO",
                        severity=sev,
                        category="profitability",
                        description=f"Índice de eficiência elevado: {eff:.1%}",
                        detail="Quanto maior o índice, mais pesada a estrutura de custos",
                    )
                )

        n_pdd = thr.get("pdd_growth_years", 3)
        if len(years) >= n_pdd:
            pdds = [metrics[y].get("pdd_ratio") for y in years[-n_pdd:]]
            if all(p is not None for p in pdds) and _is_ascending(pdds):
                report.risks.append(
                    Risk(
                        code="BANK_RISING_PDD",
                        severity="high",
                        category="credit",
                        description=f"PDD/Carteira crescendo {n_pdd} anos: "
                        f"{pdds[0]:.2%} → {pdds[-1]:.2%}",
                    )
                )

        # ROE caindo consecutivamente
        n_roe = thr.get("ni_growth_negative_years", 2) + 1
        if len(years) >= n_roe:
            roes = [metrics[y].get("roe") for y in years[-n_roe:]]
            if all(r is not None for r in roes) and _is_descending(roes):
                report.risks.append(
                    Risk(
                        code="BANK_FALLING_ROE",
                        severity="medium",
                        category="profitability",
                        description=f"ROE em queda por {n_roe} anos: {roes[0]:.1%} → {roes[-1]:.1%}",
                    )
                )

    # ── Regras industriais (+ setores derivados) ──────────────────────────────

    def _check_industrial(
        self,
        report: RiskReport,
        metrics: dict[int, dict],
        cfg: SectorConfig,
        thr: dict,
    ) -> None:
        years = sorted(metrics.keys())
        last = metrics[years[-1]]

        # Alavancagem
        nd_ebitda = last.get("nd_ebitda")
        if nd_ebitda is not None:
            if nd_ebitda > thr.get("nd_ebitda_critical", 5.0):
                sev = "critical"
            elif nd_ebitda > thr.get("nd_ebitda_high", 3.5):
                sev = "high"
            elif nd_ebitda > thr.get("nd_ebitda_medium", 2.5):
                sev = "medium"
            else:
                sev = None
            if sev:
                report.risks.append(
                    Risk(
                        code="HIGH_LEVERAGE",
                        severity=sev,
                        category="leverage",
                        description=f"DL/EBITDA elevada: {nd_ebitda:.1f}x",
                        detail=f"Threshold ({cfg.sector_type}): "
                        f"médio={thr.get('nd_ebitda_medium', 2.5):.1f}x  "
                        f"alto={thr.get('nd_ebitda_high', 3.5):.1f}x",
                    )
                )

        # Cobertura de juros
        ic = last.get("interest_coverage")
        if ic is not None:
            if ic < thr.get("interest_coverage_critical", 1.5):
                sev = "critical"
            elif ic < thr.get("interest_coverage_high", 3.0):
                sev = "high"
            else:
                sev = None
            if sev:
                report.risks.append(
                    Risk(
                        code="LOW_INTEREST_COVERAGE",
                        severity=sev,
                        category="leverage",
                        description=f"Cobertura de juros baixa: {ic:.1f}x",
                    )
                )

        # Compressão de margem EBITDA
        n_comp = thr.get("margin_compression_years", 3)
        if len(years) >= n_comp:
            margins = [metrics[y].get("ebitda_margin") for y in years[-n_comp:]]
            if all(m is not None for m in margins) and _is_descending(margins):
                report.risks.append(
                    Risk(
                        code="MARGIN_COMPRESSION",
                        severity="high",
                        category="profitability",
                        description=f"Margem EBITDA caindo {n_comp} anos: "
                        f"{margins[0]:.1%} → {margins[-1]:.1%}",
                    )
                )

        # Margem bruta mínima (retail)
        gm_min = thr.get("gross_margin_min_medium")
        if gm_min is not None:
            gm = last.get("gross_margin")
            if gm is not None and gm < gm_min:
                report.risks.append(
                    Risk(
                        code="LOW_GROSS_MARGIN",
                        severity="medium",
                        category="profitability",
                        description=f"Margem bruta baixa: {gm:.1%} (mín. esperado: {gm_min:.1%})",
                    )
                )

        # Margem EBITDA mínima (oil_gas, mining, telecom)
        em_min = thr.get("ebitda_margin_min_high")
        if em_min is not None:
            em = last.get("ebitda_margin")
            if em is not None and em < em_min:
                report.risks.append(
                    Risk(
                        code="LOW_EBITDA_MARGIN",
                        severity="high",
                        category="profitability",
                        description=f"Margem EBITDA abaixo do esperado p/ setor: "
                        f"{em:.1%} (mín. {em_min:.1%})",
                    )
                )

        # FCF negativo
        if thr.get("fcf_negative", False):
            fcf = last.get("fcf")
            if fcf is not None and fcf < 0:
                report.risks.append(
                    Risk(
                        code="NEGATIVE_FCF",
                        severity="medium",
                        category="cashflow",
                        description=f"FCF negativo: R$ {fcf:,.0f} mil",
                    )
                )

        # Yield de dividendos baixo (utilities)
        dy_min = thr.get("dividend_yield_min_medium")
        if dy_min is not None:
            dy = last.get("dividend_yield")
            if dy is not None and dy < dy_min:
                report.risks.append(
                    Risk(
                        code="LOW_DIVIDEND_YIELD",
                        severity="medium",
                        category="valuation",
                        description=f"Dividend yield baixo para utilities: {dy:.1%} (mín. {dy_min:.1%})",
                    )
                )

    # ── Regras comuns (todos os setores) ──────────────────────────────────────

    def _check_common(self, report: RiskReport, metrics: dict[int, dict], thr: dict) -> None:
        years = sorted(metrics.keys())
        last = metrics[years[-1]]

        # Lucro líquido negativo
        ni = last.get("net_income")
        if ni is not None and ni < 0:
            report.risks.append(
                Risk(
                    code="NEGATIVE_NET_INCOME",
                    severity="critical",
                    category="profitability",
                    description=f"Prejuízo em {years[-1]}: R$ {ni:,.0f} mil",
                )
            )

        # Lucro caindo N anos consecutivos
        n_neg = thr.get("ni_growth_negative_years", 2)
        if len(years) >= n_neg:
            growths = [metrics[y].get("net_income_growth") for y in years[-n_neg:]]
            if all(g is not None and g < 0 for g in growths):
                report.risks.append(
                    Risk(
                        code="FALLING_NET_INCOME",
                        severity="medium",
                        category="growth",
                        description=f"Lucro em queda por {n_neg} anos consecutivos",
                        detail="  ".join(
                            f"{years[-(n_neg - i)]}: {g:.1%}" for i, g in enumerate(growths)
                        ),
                    )
                )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_metrics(self, ticker: str) -> dict[int, dict]:
        d = self.output_dir / ticker
        if not d.exists():
            return {}
        result = {}
        for f in sorted(d.glob("metrics_*.json")):
            try:
                year = int(f.stem.split("_")[1])
                result[year] = json.loads(f.read_text())
            except Exception:
                pass
        return result

    @staticmethod
    def _save(report: RiskReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_ascending(values: list) -> bool:
    return all(values[i] < values[i + 1] for i in range(len(values) - 1))


def _is_descending(values: list) -> bool:
    return all(values[i] > values[i + 1] for i in range(len(values) - 1))


def _max_severity(risks: list[Risk]) -> Severity:
    if not risks:
        return "low"
    return max((r.severity for r in risks), key=lambda s: _SEV_ORDER.index(s))


# ── Função de alto nível ──────────────────────────────────────────────────────


def assess_risk(ticker: str, force: bool = False) -> RiskReport:
    """Avalia e persiste relatório de riscos usando thresholds do setor."""
    return RiskEngine().assess(ticker, force=force)
