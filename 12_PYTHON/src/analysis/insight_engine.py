"""
insight_engine.py
-----------------
Gera insights automáticos cruzando métricas financeiras com contexto macroeconômico.

Nesta versão (Fase 3), os insights são gerados por regras determinísticas.
Na Fase 4, serão enriquecidos com LLM (Claude API).

Exemplos de insights gerados:
  - "BBAS3 tem ROE de 21% com carteira crescendo 12% — risco de crédito latente"
  - "WEGE3: FCF yield de 4% com crescimento de 15% — valuação exigente"
  - "Selic em queda beneficia bancos via menor custo de captação"

Uso:
    from src.analysis.insight_engine import InsightEngine

    engine = InsightEngine()
    insights = engine.generate("BBAS3")
    for i in insights:
        print(i)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Insight:
    ticker: str
    category: str  # "valuation", "growth", "quality", "risk", "macro"
    severity: str  # "positive", "neutral", "negative"
    title: str
    body: str
    generated_at: str = field(default_factory=lambda: str(date.today()))
    source: str = "rules"  # "rules" ou "llm" (Fase 4)

    def __str__(self) -> str:
        icon = {"positive": "+", "neutral": "~", "negative": "!"}
        return f"[{icon.get(self.severity, '?')}] {self.title}: {self.body}"


class InsightEngine:
    """
    Gera insights a partir de métricas e risco calculados.

    Args:
        output_dir: Raiz de data/output/ (default: via settings)
    """

    def __init__(self, output_dir: Path | None = None):
        from config.settings import settings

        self.output_dir = output_dir or settings.data_output

    def generate(self, ticker: str, force: bool = False) -> list[Insight]:
        """Gera e persiste lista de insights para um ticker."""
        output_path = self.output_dir / ticker / "insights.json"
        if output_path.exists() and not force:
            try:
                data = json.loads(output_path.read_text())
                return [Insight(**i) for i in data]
            except Exception:
                pass

        metrics = self._load_latest_metrics(ticker)
        risk = self._load_risk(ticker)
        valuation = self._load_valuation(ticker)

        if not metrics:
            log.warning(f"[{ticker}] sem métricas — execute 'analyze' antes")
            return []

        info = self._ticker_info(ticker)
        is_bank = info.get("type") == "bank"
        insights: list[Insight] = []

        insights.extend(self._insights_rentabilidade(ticker, metrics, is_bank))
        insights.extend(self._insights_crescimento(ticker, metrics, is_bank))
        insights.extend(self._insights_valuation(ticker, valuation))
        insights.extend(self._insights_risco(ticker, risk))

        self._save(insights, output_path)
        log.info(f"[{ticker}] {len(insights)} insights gerados")
        return insights

    # ── Rentabilidade ─────────────────────────────────────────────────────────

    def _insights_rentabilidade(self, ticker: str, m: dict, is_bank: bool) -> list[Insight]:
        insights = []
        if is_bank:
            roe = m.get("roe")
            if roe is not None:
                if roe >= 0.20:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="quality",
                            severity="positive",
                            title="ROE excelente",
                            body=f"ROE de {roe:.1%} em {m.get('year')} — acima do custo de capital (~13%). "
                            f"Banco gera valor ao acionista.",
                        )
                    )
                elif roe >= 0.12:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="quality",
                            severity="neutral",
                            title="ROE adequado",
                            body=f"ROE de {roe:.1%} — suficiente para cobrir o custo de capital.",
                        )
                    )
                else:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="quality",
                            severity="negative",
                            title="ROE abaixo do custo de capital",
                            body=f"ROE de {roe:.1%} — banco destrói valor ao acionista ao COE estimado de ~13%.",
                        )
                    )

            eff = m.get("efficiency_ratio")
            if eff is not None:
                if eff < 0.45:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="quality",
                            severity="positive",
                            title="Eficiência operacional elevada",
                            body=f"Índice de eficiência de {eff:.1%} — melhor que média do setor (~50%).",
                        )
                    )
                elif eff > 0.60:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="quality",
                            severity="negative",
                            title="Estrutura de custos pesada",
                            body=f"Índice de eficiência de {eff:.1%} — despesas operacionais consomem {eff:.0%} do resultado bruto.",
                        )
                    )
        else:
            m.get("net_margin")
            roe = m.get("roe")
            roic = m.get("roic")
            if roic is not None and roe is not None:
                if roic >= 0.20 and roe >= 0.20:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="quality",
                            severity="positive",
                            title="Rentabilidade excepcional",
                            body=f"ROIC={roic:.1%}, ROE={roe:.1%} — empresa de alta qualidade com retorno bem acima do custo de capital.",
                        )
                    )

        return insights

    # ── Crescimento ───────────────────────────────────────────────────────────

    def _insights_crescimento(self, ticker: str, m: dict, is_bank: bool) -> list[Insight]:
        insights = []
        if is_bank:
            ni_growth = m.get("net_income_growth")
            nii_growth = m.get("nii_growth")
            if ni_growth is not None and nii_growth is not None:
                if ni_growth > 0.15 and nii_growth > 0.10:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="growth",
                            severity="positive",
                            title="Crescimento robusto",
                            body=f"Lucro líquido cresceu {ni_growth:.1%} e NII {nii_growth:.1%} no ano — momentum operacional forte.",
                        )
                    )
                elif ni_growth < -0.10:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="growth",
                            severity="negative",
                            title="Queda no lucro",
                            body=f"Lucro líquido caiu {ni_growth:.1%} no ano — monitorar tendência nos próximos trimestres.",
                        )
                    )
        else:
            rev_growth = m.get("revenue_growth")
            if rev_growth is not None:
                if rev_growth > 0.15:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="growth",
                            severity="positive",
                            title="Crescimento de receita acelerado",
                            body=f"Receita cresceu {rev_growth:.1%} — expansão relevante de volume/preço.",
                        )
                    )
                elif rev_growth < 0:
                    insights.append(
                        Insight(
                            ticker=ticker,
                            category="growth",
                            severity="negative",
                            title="Contração de receita",
                            body=f"Receita recuou {rev_growth:.1%} — investigar perda de volume vs pressão de preço.",
                        )
                    )

        return insights

    # ── Valuation ─────────────────────────────────────────────────────────────

    def _insights_valuation(self, ticker: str, valuation: dict | None) -> list[Insight]:
        if not valuation:
            return []
        insights = []
        base = valuation.get("scenarios", {}).get("base", {})
        upside = base.get("upside")
        fv = base.get("fair_value")
        if upside is not None and fv is not None:
            if upside > 0.30:
                insights.append(
                    Insight(
                        ticker=ticker,
                        category="valuation",
                        severity="positive",
                        title="Desconto expressivo vs fair value",
                        body=f"Upside de {upside:.1%} no cenário base — preço atual oferece margem de segurança relevante.",
                    )
                )
            elif upside < -0.20:
                insights.append(
                    Insight(
                        ticker=ticker,
                        category="valuation",
                        severity="negative",
                        title="Ação cara vs fair value",
                        body=f"Downside de {upside:.1%} no cenário base — múltiplos precificam crescimento otimista.",
                    )
                )
            else:
                insights.append(
                    Insight(
                        ticker=ticker,
                        category="valuation",
                        severity="neutral",
                        title="Valuação próxima ao fair value",
                        body=f"Upside de {upside:.1%} no cenário base — ação negociada próxima ao valor intrínseco estimado.",
                    )
                )
        return insights

    # ── Riscos ────────────────────────────────────────────────────────────────

    def _insights_risco(self, ticker: str, risk: dict | None) -> list[Insight]:
        if not risk or risk.get("overall_severity") == "low":
            return []
        insights = []
        severity = risk.get("overall_severity", "low")
        count = risk.get("risk_count", 0)
        if severity in ("high", "critical") and count > 0:
            top_risks = [
                r["description"]
                for r in risk.get("risks", [])
                if r.get("severity") in ("high", "critical")
            ][:2]
            insights.append(
                Insight(
                    ticker=ticker,
                    category="risk",
                    severity="negative",
                    title=f"Alertas de risco ({severity.upper()})",
                    body=f"{count} risco(s) identificados. Principais: {'; '.join(top_risks)}.",
                )
            )
        return insights

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_latest_metrics(self, ticker: str) -> dict | None:
        d = self.output_dir / ticker
        files = sorted(d.glob("metrics_*.json")) if d.exists() else []
        return json.loads(files[-1].read_text()) if files else None

    def _load_risk(self, ticker: str) -> dict | None:
        p = self.output_dir / ticker / "risk_report.json"
        return json.loads(p.read_text()) if p.exists() else None

    def _load_valuation(self, ticker: str) -> dict | None:
        p = self.output_dir / ticker / "valuation.json"
        return json.loads(p.read_text()) if p.exists() else None

    @staticmethod
    def _ticker_info(ticker: str) -> dict:
        from config.settings import settings

        return {t["ticker"]: t for t in settings.tickers}.get(ticker.upper(), {})

    @staticmethod
    def _save(insights: list[Insight], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([i.__dict__ for i in insights], ensure_ascii=False, indent=2))
