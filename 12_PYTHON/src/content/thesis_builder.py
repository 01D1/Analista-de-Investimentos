"""
thesis_builder.py
-----------------
Constrói ou atualiza a tese de investimento completa de um ticker,
usando todas as análises disponíveis + Claude API.

Estrutura da tese (10 seções — PROMPT_CONSTRUTOR_TESE.md):
  1. Resumo Executivo
  2. O Negócio (modelo, vantagens competitivas)
  3. Drivers de Crescimento
  4. Qualidade Financeira (métricas históricas)
  5. Governança & ESG
  6. Riscos Principais
  7. Valuation (múltiplos + modelo)
  8. Catalisadores
  9. Fatores de Invalidação da Tese
  10. Conclusão e Posicionamento

Output: 03_COMPANIES/{TICKER}/TESE_DE_INVESTIMENTO.md

Uso:
    from src.content.thesis_builder import build_thesis

    path = build_thesis("BBAS3")
    path = build_thesis("WEGE3", force=True)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)


class ThesisBuilder:
    """
    Constrói tese de investimento completa com Claude API.

    Agrega métricas históricas, valuation, risco e insights
    num documento de tese estruturado salvo no vault Obsidian.
    """

    def __init__(self):
        from config.settings import settings

        self.settings = settings

    def build(self, ticker: str, force: bool = False) -> Path:
        """
        Constrói a tese de investimento para o ticker.

        Args:
            ticker: Código do ticker
            force:  Sobrescrever tese existente

        Returns:
            Path do arquivo gerado em 03_COMPANIES/{ticker}/
        """
        output_dir = self.settings.vault_path / "03_COMPANIES" / ticker
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "TESE_DE_INVESTIMENTO.md"

        if output_path.exists() and not force:
            log.info(f"[Tese] já existe: {output_path} — use force=True para atualizar")
            return output_path

        log.info(f"[Tese] construindo tese para {ticker}...")

        # Carregar todos os dados disponíveis
        all_metrics = self._load_all_metrics(ticker)
        risk = self._load_risk(ticker)
        valuation = self._load_valuation(ticker)
        insights = self._load_insights(ticker)
        info = self._ticker_info(ticker)

        if not all_metrics:
            log.warning(f"[Tese] [{ticker}] sem métricas — execute 'analyze' primeiro")
            output_path.write_text(
                f"# Tese de Investimento — {ticker}\n\n"
                "> Sem dados disponíveis. Execute `python -m src.main analyze --ticker {ticker}` primeiro.\n",
                encoding="utf-8",
            )
            return output_path

        # Montar prompt com contexto completo
        user_prompt = self._build_user_prompt(ticker, all_metrics, risk, valuation, insights, info)

        # Gerar com LLM
        content = self._generate_with_llm(ticker, user_prompt)

        # Salvar
        self._save(content, output_path, ticker, info)
        log.success(f"[Tese] salva em {output_path}")
        return output_path

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _build_user_prompt(
        self,
        ticker: str,
        all_metrics: dict[int, dict],
        risk: dict | None,
        valuation: dict | None,
        insights: list[dict],
        info: dict,
    ) -> str:
        from src.valuation.sector_config import SectorConfig

        cfg = SectorConfig.for_ticker(ticker)

        years = sorted(all_metrics.keys())
        last = all_metrics[years[-1]]

        lines = [
            f"# Dados para Tese de Investimento — {ticker}",
            f"**Empresa**: {info.get('name', ticker)}",
            f"**Setor**: {cfg.sector_type} | **Modelo Financeiro**: {cfg.financial_model}",
            f"**Período coberto**: {years[0]}–{years[-1]} ({len(years)} anos)",
            "",
        ]

        # Métricas históricas — tabela por ano
        key_metrics = last.get("key_metrics") or cfg.key_metrics
        lines.append("## Histórico de Métricas")
        header = "| Métrica | " + " | ".join(str(y) for y in years) + " |"
        separator = "|---------|" + "---------|" * len(years)
        lines += [header, separator]

        for metric in key_metrics:
            row_vals = []
            for y in years:
                v = all_metrics[y].get(metric)
                row_vals.append(_fmt(metric, v) if v is not None else "—")
            lines.append(f"| {_label(metric)} | " + " | ".join(row_vals) + " |")

        # Crescimentos
        growth_keys = [
            "revenue_growth",
            "net_income_growth",
            "ebitda_growth",
            "nii_growth",
            "loan_growth",
        ]
        growth_rows = [(k, last.get(k)) for k in growth_keys if last.get(k) is not None]
        if growth_rows:
            lines.append("\n## Crescimento (último período)")
            for k, v in growth_rows:
                lines.append(f"- {_label(k)}: {_fmt(k, v)}")

        # Preço e múltiplos de mercado
        mkt_keys = ["market_price", "pb_ratio", "pe_ratio", "dividend_yield", "ev_ebitda"]
        mkt_items = [(k, last.get(k)) for k in mkt_keys if last.get(k) is not None]
        if mkt_items:
            lines.append("\n## Dados de Mercado (último período)")
            for k, v in mkt_items:
                lines.append(f"- {_label(k)}: {_fmt(k, v)}")

        # Risco
        if risk:
            lines.append(f"\n## Análise de Risco — {risk.get('overall_severity', '?').upper()}")
            for r in risk.get("risks") or []:
                sev = r.get("severity", "?").upper()
                lines.append(f"- [{sev}] {r.get('description', '')}")

        # Valuation
        if valuation:
            method = valuation.get("method", "?")
            lines.append(f"\n## Valuation — Método: {method}")
            for scenario, data in (valuation.get("scenarios") or {}).items():
                fv = data.get("fair_value")
                up = data.get("upside")
                if fv and up is not None:
                    lines.append(
                        f"- **{scenario.title()}**: Fair Value R$ {fv:,.2f} "
                        f"({up:+.1%} upside/downside)"
                    )

        # Insights gerados por regras
        if insights:
            lines.append("\n## Insights Identificados")
            for ins in insights:
                sev = ins.get("severity", "neutral")
                icon = {"positive": "+", "negative": "!", "neutral": "~"}.get(sev, "?")
                title = ins.get("title", "")
                body = ins.get("body", "")
                lines.append(f"- [{icon}] **{title}**: {body}")

        lines += [
            "",
            "## Instruções para a Tese",
            "Construa a tese de investimento completa com as 10 seções do template.",
            "Use os dados históricos para suportar cada afirmação.",
            f"O setor é '{cfg.sector_type}' — adapte a linguagem e métricas conforme o setor.",
            "Seja analítico, factual e use os números fornecidos.",
            "Inclua recomendação final (Compra / Neutro / Venda) com preço-alvo baseado no valuation.",
            "Formato: Markdown compatível com Obsidian.",
        ]

        return "\n".join(lines)

    # ── LLM ──────────────────────────────────────────────────────────────────

    def _generate_with_llm(self, ticker: str, user_prompt: str) -> str:
        from src.content.llm_client import get_llm_client

        client = get_llm_client()

        system_parts = []

        # Persona analista
        analista = client.prompt_analista()
        if analista:
            system_parts.append(analista.strip())

        # Prompt construtor de tese
        construtor = client.prompt_construtor_tese()
        if construtor:
            system_parts.append(construtor.strip())

        # Template da tese
        template_path = (
            self.settings.vault_path / "00_META" / "INTELLIGENCE_SYSTEM" / "THESIS_TEMPLATE.md"
        )
        if template_path.exists():
            tmpl = template_path.read_text(encoding="utf-8")
            system_parts.append(f"\n## Template de Tese\n\n{tmpl}")

        system_parts.append(
            "\n## Regras de Saída\n"
            "- Markdown com frontmatter YAML no início\n"
            "- Dados em R$ mil — converta para milhões/bilhões onde aplicável\n"
            "- Cite os anos/valores explicitamente ao fazer afirmações\n"
            "- Seção de Riscos deve listar pelo menos 3 riscos com mitigadores\n"
            "- Seção de Valuation deve apresentar os 3 cenários (base, otimista, pessimista)\n"
            "- Termine com box de Tese em 3 bullet points\n"
        )

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        if not self.settings.anthropic_api_key:
            log.warning("[Tese] ANTHROPIC_API_KEY não configurada — retornando stub")
            return (
                f"# Tese de Investimento — {ticker} (Stub)\n\n"
                "> Configure ANTHROPIC_API_KEY no .env\n\n"
                f"```\n{user_prompt[:600]}\n...\n```\n"
            )

        log.info(f"[Tese] [{ticker}] chamando Claude (tese completa)...")
        return client.generate(
            user_message=user_prompt,
            system_prompt=system_prompt,
            use_cache=True,
            max_tokens=6000,  # Tese longa
            temperature=0.3,
        )

    # ── Persistência ─────────────────────────────────────────────────────────

    def _save(self, content: str, path: Path, ticker: str, info: dict) -> None:
        today = date.today()
        frontmatter = (
            "---\n"
            f"ticker: {ticker}\n"
            f"name: {info.get('name', ticker)}\n"
            f"sector: {info.get('sector', 'unknown')}\n"
            f"updated: {today}\n"
            "type: tese-de-investimento\n"
            "tags: [tese, valuation, analise]\n"
            "generated_by: intelligence-system\n"
            "---\n\n"
        )
        final = content if content.startswith("---") else frontmatter + content
        path.write_text(final, encoding="utf-8")

    # ── Loaders ──────────────────────────────────────────────────────────────

    def _load_all_metrics(self, ticker: str) -> dict[int, dict]:
        d = self.settings.data_output / ticker
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

    def _load_risk(self, ticker: str) -> dict | None:
        p = self.settings.data_output / ticker / "risk_report.json"
        return json.loads(p.read_text()) if p.exists() else None

    def _load_valuation(self, ticker: str) -> dict | None:
        p = self.settings.data_output / ticker / "valuation.json"
        return json.loads(p.read_text()) if p.exists() else None

    def _load_insights(self, ticker: str) -> list[dict]:
        p = self.settings.data_output / ticker / "insights.json"
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except Exception:
            return []

    def _ticker_info(self, ticker: str) -> dict:
        return {t["ticker"]: t for t in self.settings.tickers}.get(ticker.upper(), {})


# ── Helpers de formatação ─────────────────────────────────────────────────────

_LABELS: dict[str, str] = {
    "roe": "ROE",
    "roa": "ROA",
    "rote": "ROTE",
    "roic": "ROIC",
    "nii_margin": "NIM",
    "efficiency_ratio": "Índice de Eficiência",
    "leverage": "Alavancagem",
    "pdd_ratio": "PDD/Carteira",
    "ebitda_margin": "Margem EBITDA",
    "net_margin": "Margem Líquida",
    "gross_margin": "Margem Bruta",
    "ebit_margin": "Margem EBIT",
    "nd_ebitda": "DL/EBITDA",
    "interest_coverage": "Cobertura de Juros",
    "fcf": "FCF",
    "pb_ratio": "P/VP",
    "pe_ratio": "P/L",
    "dividend_yield": "DY",
    "ev_ebitda": "EV/EBITDA",
    "market_price": "Preço de Mercado",
    "revenue_growth": "Crescimento Receita",
    "net_income_growth": "Crescimento Lucro",
    "ebitda_growth": "Crescimento EBITDA",
    "nii_growth": "Crescimento NII",
    "loan_growth": "Crescimento Carteira",
    "asset_growth": "Crescimento Ativos",
}

_PCTS = {
    "roe",
    "roa",
    "rote",
    "roic",
    "nii_margin",
    "efficiency_ratio",
    "pdd_ratio",
    "ebitda_margin",
    "net_margin",
    "gross_margin",
    "ebit_margin",
    "fcf_conversion",
    "fcf_yield",
    "capex_to_revenue",
    "revenue_growth",
    "ebitda_growth",
    "net_income_growth",
    "nii_growth",
    "loan_growth",
    "asset_growth",
    "dividend_yield",
}


def _label(k: str) -> str:
    return _LABELS.get(k, k.replace("_", " ").title())


def _fmt(k: str, v) -> str:
    if v is None:
        return "—"
    if k in _PCTS:
        return f"{v:.1%}"
    if k in ("leverage", "nd_ebitda", "interest_coverage", "pb_ratio", "pe_ratio", "ev_ebitda"):
        return f"{v:.1f}x"
    if k == "fcf":
        return f"R$ {v / 1000:,.0f} mi"
    if k == "market_price":
        return f"R$ {v:,.2f}"
    return str(v)


# ── Função de alto nível ──────────────────────────────────────────────────────


def build_thesis(ticker: str, force: bool = False) -> Path:
    """Constrói tese de investimento completa e salva no vault."""
    return ThesisBuilder().build(ticker, force=force)
