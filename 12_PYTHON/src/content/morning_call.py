"""
morning_call.py
---------------
Gera o morning call diário automaticamente:
  1. Coleta dados de mercado (índices, câmbio, commodities) via yfinance
  2. Carrega insights recentes dos tickers ativos
  3. Envia tudo ao Claude com o template do vault
  4. Salva output em 14_OUTPUTS/morning_call_{YYYY-MM-DD}.md

Uso:
    from src.content.morning_call import generate_morning_call

    path = generate_morning_call()
    print(f"Salvo em: {path}")

    # Via CLI:
    python -m src.main content morning-call
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

log = get_logger(__name__)

# Ativos de mercado monitorados
_MARKET_TICKERS = {
    "indices": {
        "IBOV": "^BVSP",
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DAX": "^GDAXI",
        "Shanghai": "000001.SS",
    },
    "cambio": {
        "USD/BRL": "BRL=X",
        "EUR/BRL": "EURBRL=X",
        "EUR/USD": "EURUSD=X",
    },
    "commodities": {
        "Petróleo WTI": "CL=F",
        "Petróleo Brent": "BZ=F",
        "Minério de Ferro": "TIOF1.SG",
        "Ouro": "GC=F",
        "Milho": "ZC=F",
        "Soja": "ZS=F",
    },
    "juros": {
        "Treasury 10Y": "^TNX",
        "Treasury 2Y": "^IRX",
    },
}


class MorningCallGenerator:
    """
    Orquestra a geração do morning call diário.

    Fluxo:
        1. fetch_market_data() — yfinance last 2 days
        2. load_ticker_context() — insights dos tickers ativos
        3. build_prompt() — monta contexto estruturado
        4. generate_with_llm() — chama Claude
        5. save() — grava no vault
    """

    def __init__(self):
        from config.settings import settings

        self.settings = settings
        self.output_dir: Path = settings.vault_path / "14_OUTPUTS"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, reference_date: date | None = None, force: bool = False) -> Path:
        """
        Gera o morning call para a data de referência.

        Args:
            reference_date: Data do call (default: hoje)
            force:          Regerar mesmo se já existir

        Returns:
            Path do arquivo gerado no vault
        """
        ref = reference_date or date.today()
        output_path = self.output_dir / f"morning_call_{ref}.md"

        if output_path.exists() and not force:
            log.info(f"[MorningCall] já existe: {output_path.name} — use force=True para regerar")
            return output_path

        log.info(f"[MorningCall] gerando para {ref}...")

        # 1. Dados de mercado
        market = self.fetch_market_data()

        # 2. Contexto dos tickers
        ticker_context = self.load_ticker_context()

        # 3. Montar prompt
        user_prompt = self.build_user_prompt(ref, market, ticker_context)

        # 4. Gerar com LLM
        content = self.generate_with_llm(user_prompt)

        # 5. Salvar
        self.save(content, output_path, ref)
        log.success(f"[MorningCall] salvo em {output_path}")
        return output_path

    # ── Coleta de dados ───────────────────────────────────────────────────────

    def fetch_market_data(self) -> dict[str, dict[str, Any]]:
        """Coleta variações de mercado dos últimos 2 dias via yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            log.warning("[MorningCall] yfinance não instalado — dados de mercado indisponíveis")
            return {}

        result: dict[str, dict[str, Any]] = {}
        start = (date.today() - timedelta(days=7)).isoformat()  # 7 dias para garantir 2 pregões

        for category, tickers in _MARKET_TICKERS.items():
            result[category] = {}
            for name, symbol in tickers.items():
                try:
                    df = yf.download(symbol, start=start, progress=False, auto_adjust=True)
                    if df.empty or len(df) < 2:
                        continue
                    df = df.sort_index()
                    close = df["Close"].squeeze()  # handles MultiIndex columns from yfinance
                    last = float(close.iloc[-1])
                    prev = float(close.iloc[-2])
                    change = (last - prev) / prev if prev else 0.0
                    result[category][name] = {
                        "last": round(last, 2),
                        "change": round(change * 100, 2),  # em %
                        "date": str(df.index[-1].date()),
                    }
                except Exception as exc:
                    log.debug(f"[MorningCall] falha ao coletar {symbol}: {exc}")

        log.info(f"[MorningCall] mercado: {sum(len(v) for v in result.values())} ativos coletados")
        return result

    # ── Contexto dos tickers ──────────────────────────────────────────────────

    def load_ticker_context(self) -> list[dict]:
        """Carrega insights e métricas recentes dos tickers ativos."""
        context = []
        output_dir = self.settings.data_output

        for ticker in self.settings.active_tickers:
            ticker_dir = output_dir / ticker
            if not ticker_dir.exists():
                continue

            entry: dict[str, Any] = {"ticker": ticker}

            # Insights
            insights_path = ticker_dir / "insights.json"
            if insights_path.exists():
                try:
                    insights = json.loads(insights_path.read_text())
                    entry["insights"] = [
                        f"[{i.get('severity', '?').upper()}] {i.get('title', '')}: {i.get('body', '')}"
                        for i in insights[:3]  # top 3
                    ]
                except Exception:
                    pass

            # Risco
            risk_path = ticker_dir / "risk_report.json"
            if risk_path.exists():
                try:
                    risk = json.loads(risk_path.read_text())
                    entry["risk_severity"] = risk.get("overall_severity", "unknown")
                    entry["risk_count"] = risk.get("risk_count", 0)
                except Exception:
                    pass

            # Valuation upside
            val_path = ticker_dir / "valuation.json"
            if val_path.exists():
                try:
                    val = json.loads(val_path.read_text())
                    upside = val.get("scenarios", {}).get("base", {}).get("upside")
                    if upside is not None:
                        entry["upside"] = round(upside * 100, 1)
                except Exception:
                    pass

            if len(entry) > 1:
                context.append(entry)

        return context

    # ── Montagem do prompt ────────────────────────────────────────────────────

    def build_user_prompt(self, ref: date, market: dict, ticker_context: list[dict]) -> str:
        """Monta o prompt do usuário com todos os dados estruturados."""
        lines = [
            f"# Morning Call — {ref.strftime('%d/%m/%Y')}",
            "",
            "## Dados de Mercado",
        ]

        for category, assets in market.items():
            if not assets:
                continue
            lines.append(f"\n### {category.title()}")
            for name, data in assets.items():
                arrow = "▲" if data["change"] >= 0 else "▼"
                sign = "+" if data["change"] >= 0 else ""
                lines.append(
                    f"- **{name}**: {data['last']:,.2f} ({arrow} {sign}{data['change']:.2f}%)"
                )

        lines += ["", "## Portfólio Monitorado"]
        if ticker_context:
            for t in ticker_context:
                ticker = t["ticker"]
                risk = t.get("risk_severity", "?")
                upside = t.get("upside")
                upside_str = f" | Upside: {upside:+.1f}%" if upside is not None else ""
                lines.append(f"\n### {ticker} [Risco: {risk.upper()}{upside_str}]")
                for ins in t.get("insights", []):
                    lines.append(f"  - {ins}")
        else:
            lines.append("_Nenhum dado disponível — execute 'analyze' primeiro._")

        lines += [
            "",
            "## Instruções",
            "Com base nos dados acima, escreva o morning call completo seguindo o template padrão.",
            "Inclua: Mundo, Brasil, Commodities, Impactos no Portfólio.",
            "Seja objetivo, factual e em português brasileiro formal.",
            "Destaque os 2-3 pontos mais relevantes para o dia.",
        ]

        return "\n".join(lines)

    # ── LLM ──────────────────────────────────────────────────────────────────

    def generate_with_llm(self, user_prompt: str) -> str:
        """Chama Claude para gerar o morning call."""
        from src.content.llm_client import get_llm_client

        client = get_llm_client()

        # System prompt: analista persona + redator research
        system_parts = []

        analista = client.prompt_analista()
        if analista:
            system_parts.append(analista.strip())

        # Template do morning call
        template_path = self.settings.vault_path / "14_OUTPUTS" / "MORNING_CALL.md"
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
            system_parts.append(f"\n## Template de Morning Call\n\n{template}")

        system_parts.append(
            "\n## Regras de Formatação\n"
            "- Use Markdown compatível com Obsidian\n"
            "- Tags no cabeçalho YAML: type: morning-call\n"
            "- Não use julgamentos subjetivos sem dados\n"
            "- Termine com seção 'Radar do Dia' com 3 bullet points de atenção\n"
        )

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        if not self.settings.anthropic_api_key:
            log.warning("[MorningCall] ANTHROPIC_API_KEY não configurada — retornando stub")
            return _stub_morning_call(user_prompt)

        log.info("[MorningCall] chamando Claude...")
        return client.generate(
            user_message=user_prompt,
            system_prompt=system_prompt,
            use_cache=True,
            max_tokens=3000,
            temperature=0.4,
        )

    # ── Persistência ─────────────────────────────────────────────────────────

    def save(self, content: str, path: Path, ref: date) -> None:
        """Salva o morning call no vault com frontmatter YAML."""
        frontmatter = (
            "---\n"
            f"date: {ref}\n"
            "type: morning-call\n"
            "tags: [morning-call, mercado]\n"
            "generated_by: intelligence-system\n"
            "---\n\n"
        )

        # Se o conteúdo já tem frontmatter, não duplicar
        final = content if content.startswith("---") else frontmatter + content
        path.write_text(final, encoding="utf-8")


# ── Stub para quando API não está configurada ─────────────────────────────────


def _stub_morning_call(context: str) -> str:
    return (
        "# Morning Call — Stub\n\n"
        "> _API Claude não configurada. Configure ANTHROPIC_API_KEY no .env_\n\n"
        "## Contexto recebido\n\n"
        f"```\n{context[:500]}...\n```\n"
    )


# ── Função de alto nível ──────────────────────────────────────────────────────


def generate_morning_call(
    reference_date: date | None = None,
    force: bool = False,
) -> Path:
    """Gera o morning call diário e salva no vault Obsidian."""
    return MorningCallGenerator().generate(reference_date=reference_date, force=force)
