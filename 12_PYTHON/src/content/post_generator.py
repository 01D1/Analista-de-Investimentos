"""
post_generator.py
-----------------
Gera posts de resultados trimestrais/anuais para LinkedIn/redes sociais.

Estrutura do post (baseada em TEMPLATE_POST.md do vault):
  - Hook (primeira linha impactante)
  - Contexto (breve cenário)
  - Análise (dados quantitativos)
  - Conclusão (posicionamento)

O post é gerado com o PROMPT_REDATOR_RESEARCH.md como persona
e as métricas calculadas como dados de contexto.

Uso:
    from src.content.post_generator import generate_post

    path = generate_post("BBAS3")
    path = generate_post("WEGE3", result_type="quarterly", quarter=3, year=2024)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from src.utils.logger import get_logger

log = get_logger(__name__)

ResultType = Literal["annual", "quarterly"]


class PostGenerator:
    """
    Gera post de resultados a partir das métricas calculadas.

    O post segue o template Hook→Contexto→Análise→Conclusão
    e é salvo em 14_OUTPUTS/posts/{TICKER}_{data}.md
    """

    def __init__(self):
        from config.settings import settings

        self.settings = settings
        self.output_dir: Path = settings.vault_path / "14_OUTPUTS" / "posts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        ticker: str,
        result_type: ResultType = "annual",
        quarter: int | None = None,
        year: int | None = None,
        force: bool = False,
    ) -> Path:
        """
        Gera post para o ticker.

        Args:
            ticker:      Código do ticker (ex. "BBAS3")
            result_type: "annual" ou "quarterly"
            quarter:     Trimestre (1-4), obrigatório se result_type="quarterly"
            year:        Ano de referência (default: último disponível)
            force:       Regerar mesmo se arquivo existir

        Returns:
            Path do arquivo gerado no vault
        """
        today = date.today()
        suffix = (
            f"Q{quarter}" if result_type == "quarterly" and quarter else str(year or today.year)
        )
        filename = f"{ticker}_{suffix}_{today}.md"
        output_path = self.output_dir / filename

        if output_path.exists() and not force:
            log.info(f"[Post] já existe: {filename} — use force=True para regerar")
            return output_path

        log.info(f"[Post] gerando post {ticker} {suffix}...")

        # Carregar dados
        metrics = self._load_metrics(ticker, year)
        risk = self._load_risk(ticker)
        valuation = self._load_valuation(ticker)
        info = self._ticker_info(ticker)

        if not metrics:
            log.warning(f"[Post] [{ticker}] sem métricas — execute 'analyze' primeiro")
            output_path.write_text(
                f"# Post {ticker} — sem dados\n\n"
                "Execute `python -m src.main analyze --ticker {ticker}` primeiro.",
                encoding="utf-8",
            )
            return output_path

        # Montar prompt
        user_prompt = self._build_user_prompt(
            ticker, metrics, risk, valuation, info, result_type, quarter, suffix
        )

        # Gerar
        content = self._generate_with_llm(user_prompt)

        # Salvar
        self._save(content, output_path, ticker, suffix)
        log.success(f"[Post] salvo em {output_path}")
        return output_path

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _build_user_prompt(
        self,
        ticker: str,
        metrics: dict,
        risk: dict | None,
        valuation: dict | None,
        info: dict,
        result_type: str,
        quarter: int | None,
        period: str,
    ) -> str:
        from src.valuation.sector_config import SectorConfig

        cfg = SectorConfig.for_ticker(ticker)

        lines = [
            f"# Dados para Post de Resultados — {ticker} {period}",
            f"**Setor**: {cfg.sector_type}  |  **Nome**: {info.get('name', ticker)}",
            f"**Tipo de resultado**: {'Trimestral ' + str(quarter) + 'T' if quarter else 'Anual'}",
            "",
            "## Métricas Financeiras",
        ]

        # Métricas-chave do setor
        key_metrics = metrics.get("key_metrics") or cfg.key_metrics
        for key in key_metrics:
            val = metrics.get(key)
            if val is not None:
                lines.append(f"- **{_label(key)}**: {_fmt(key, val)}")

        # Crescimentos
        growth_keys = [
            k
            for k in [
                "revenue_growth",
                "net_income_growth",
                "ebitda_growth",
                "nii_growth",
                "loan_growth",
                "asset_growth",
            ]
            if metrics.get(k) is not None
        ]
        if growth_keys:
            lines.append("\n## Crescimentos YoY")
            for k in growth_keys:
                lines.append(f"- **{_label(k)}**: {_fmt(k, metrics[k])}")

        # Risco
        if risk:
            lines.append(f"\n## Perfil de Risco: {risk.get('overall_severity', '?').upper()}")
            for r in (risk.get("risks") or [])[:3]:
                lines.append(f"- {r.get('description', '')}")

        # Valuation
        if valuation:
            base = (valuation.get("scenarios") or {}).get("base", {})
            fv = base.get("fair_value")
            up = base.get("upside")
            method = valuation.get("method", "")
            if fv and up is not None:
                lines.append(f"\n## Valuation ({method})")
                lines.append(f"- Fair Value (base): R$ {fv:,.2f}")
                lines.append(f"- Upside/Downside: {up:+.1%}")

        lines += [
            "",
            "## Instruções para o Post",
            "Escreva um post profissional para LinkedIn seguindo exatamente o template:",
            "Hook → Contexto → Análise → Conclusão.",
            "Use dados concretos. Máximo 1.200 caracteres.",
            "Termine com 3-5 hashtags relevantes.",
            "Tom: analítico, direto, sem hype.",
        ]

        return "\n".join(lines)

    # ── LLM ──────────────────────────────────────────────────────────────────

    def _generate_with_llm(self, user_prompt: str) -> str:
        from src.content.llm_client import get_llm_client

        client = get_llm_client()

        system_parts = []

        # Persona redator
        redator = client.prompt_redator()
        if redator:
            system_parts.append(redator.strip())

        # Template do post
        template_path = self.settings.vault_path / "14_OUTPUTS" / "TEMPLATE_POST.md"
        if template_path.exists():
            tmpl = template_path.read_text(encoding="utf-8")
            system_parts.append(f"\n## Template de Post\n\n{tmpl}")

        system_parts.append(
            "\n## Regras\n"
            "- Escreva em português brasileiro\n"
            "- Dados são em R$ mil (converter para milhões/bilhões conforme necessário)\n"
            "- Seja objetivo — sem adjetivos sem dados\n"
            "- Separe o post do 'Note de Resultado' com linha horizontal (---)\n"
        )

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        if not self.settings.anthropic_api_key:
            log.warning("[Post] ANTHROPIC_API_KEY não configurada — retornando stub")
            return f"# Post Stub\n\n> Configure ANTHROPIC_API_KEY no .env\n\n```\n{user_prompt[:400]}\n```\n"

        log.info("[Post] chamando Claude...")
        return client.generate(
            user_message=user_prompt,
            system_prompt=system_prompt,
            use_cache=True,
            max_tokens=2000,
            temperature=0.5,
        )

    # ── Persistência ─────────────────────────────────────────────────────────

    def _save(self, content: str, path: Path, ticker: str, period: str) -> None:
        today = date.today()
        frontmatter = (
            "---\n"
            f"ticker: {ticker}\n"
            f"period: {period}\n"
            f"date: {today}\n"
            "type: post-resultado\n"
            "tags: [post, resultado, linkedin]\n"
            "generated_by: intelligence-system\n"
            "---\n\n"
        )
        final = content if content.startswith("---") else frontmatter + content
        path.write_text(final, encoding="utf-8")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_metrics(self, ticker: str, year: int | None) -> dict | None:
        output_dir = self.settings.data_output / ticker
        if not output_dir.exists():
            return None
        if year:
            p = output_dir / f"metrics_{year}.json"
            return json.loads(p.read_text()) if p.exists() else None
        # Último disponível
        files = sorted(output_dir.glob("metrics_*.json"))
        return json.loads(files[-1].read_text()) if files else None

    def _load_risk(self, ticker: str) -> dict | None:
        p = self.settings.data_output / ticker / "risk_report.json"
        return json.loads(p.read_text()) if p.exists() else None

    def _load_valuation(self, ticker: str) -> dict | None:
        p = self.settings.data_output / ticker / "valuation.json"
        return json.loads(p.read_text()) if p.exists() else None

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
    "nd_ebitda": "DL/EBITDA",
    "interest_coverage": "Cobertura de Juros",
    "fcf": "FCF",
    "pb_ratio": "P/VP",
    "pe_ratio": "P/L",
    "dividend_yield": "DY",
    "ev_ebitda": "EV/EBITDA",
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
    return str(v)


# ── Função de alto nível ──────────────────────────────────────────────────────


def generate_post(
    ticker: str,
    result_type: ResultType = "annual",
    quarter: int | None = None,
    year: int | None = None,
    force: bool = False,
) -> Path:
    """Gera post de resultado para o ticker e salva no vault."""
    return PostGenerator().generate(
        ticker=ticker,
        result_type=result_type,
        quarter=quarter,
        year=year,
        force=force,
    )
