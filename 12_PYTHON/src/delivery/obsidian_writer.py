"""
obsidian_writer.py
------------------
Gerencia a escrita de arquivos no vault Obsidian.

Responsabilidades:
  - Criar/atualizar notas no vault mantendo estrutura de pastas
  - Adicionar/atualizar frontmatter YAML
  - Criar backlinks automáticos entre notas de empresas
  - Registrar histórico de outputs gerados (00_META/outputs_log.md)
  - Garantir encoding UTF-8 e compatibilidade com Obsidian

Uso:
    from src.delivery.obsidian_writer import ObsidianWriter

    writer = ObsidianWriter()
    path = writer.write(
        relative_path="03_COMPANIES/BBAS3/metrics_2024.md",
        content="# BBAS3 Métricas 2024\n...",
        frontmatter={"ticker": "BBAS3", "year": 2024},
    )
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

log = get_logger(__name__)


class ObsidianWriter:
    """
    Escreve e gerencia notas no vault Obsidian.

    Args:
        vault_path: Path raiz do vault (default: via settings)
    """

    def __init__(self, vault_path: Path | None = None):
        from config.settings import settings

        self.vault = vault_path or settings.vault_path

    # ── Escrita principal ─────────────────────────────────────────────────────

    def write(
        self,
        relative_path: str,
        content: str,
        frontmatter: dict[str, Any] | None = None,
        overwrite: bool = True,
    ) -> Path:
        """
        Escreve uma nota no vault.

        Args:
            relative_path: Caminho relativo à raiz do vault (ex: "03_COMPANIES/BBAS3/tese.md")
            content:       Conteúdo Markdown
            frontmatter:   Dict de metadados YAML a mesclar/criar
            overwrite:     Sobrescrever se já existir (default True)

        Returns:
            Path absoluto do arquivo criado/atualizado
        """
        abs_path = self.vault / relative_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        if abs_path.exists() and not overwrite:
            log.info(f"[Obsidian] arquivo já existe: {relative_path}")
            return abs_path

        # Mesclar frontmatter se necessário
        final_content = _inject_frontmatter(content, frontmatter or {})
        abs_path.write_text(final_content, encoding="utf-8")

        log.info(f"[Obsidian] escrito: {relative_path}")
        self._log_output(relative_path)
        return abs_path

    def append(self, relative_path: str, content: str) -> Path:
        """Adiciona conteúdo ao fim de uma nota existente (cria se não existir)."""
        abs_path = self.vault / relative_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        existing = abs_path.read_text(encoding="utf-8") if abs_path.exists() else ""
        abs_path.write_text(existing + "\n\n" + content, encoding="utf-8")
        log.info(f"[Obsidian] atualizado: {relative_path}")
        return abs_path

    # ── Helpers por tipo de nota ──────────────────────────────────────────────

    def write_morning_call(self, content: str, ref_date: date | None = None) -> Path:
        ref = ref_date or date.today()
        return self.write(
            relative_path=f"14_OUTPUTS/morning_call_{ref}.md",
            content=content,
            frontmatter={
                "date": str(ref),
                "type": "morning-call",
                "tags": ["morning-call", "mercado"],
            },
        )

    def write_post(self, ticker: str, content: str, period: str) -> Path:
        today = date.today()
        return self.write(
            relative_path=f"14_OUTPUTS/posts/{ticker}_{period}_{today}.md",
            content=content,
            frontmatter={
                "ticker": ticker,
                "period": period,
                "date": str(today),
                "type": "post-resultado",
                "tags": ["post", "resultado"],
            },
        )

    def write_thesis(self, ticker: str, content: str, ticker_info: dict) -> Path:
        return self.write(
            relative_path=f"03_COMPANIES/{ticker}/TESE_DE_INVESTIMENTO.md",
            content=content,
            frontmatter={
                "ticker": ticker,
                "name": ticker_info.get("name", ticker),
                "sector": ticker_info.get("sector", "unknown"),
                "updated": str(date.today()),
                "type": "tese-de-investimento",
                "tags": ["tese", "valuation", "analise"],
            },
        )

    def write_metrics_summary(self, ticker: str, metrics: dict, year: int) -> Path:
        """Escreve resumo de métricas como nota no vault."""
        from src.valuation.sector_config import SectorConfig

        cfg = SectorConfig.for_ticker(ticker)

        lines = [f"# {ticker} — Métricas {year}", ""]
        key_metrics = metrics.get("key_metrics") or cfg.key_metrics
        for k in key_metrics:
            v = metrics.get(k)
            if v is not None:
                lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")

        return self.write(
            relative_path=f"03_COMPANIES/{ticker}/metrics_{year}.md",
            content="\n".join(lines),
            frontmatter={
                "ticker": ticker,
                "year": year,
                "type": "metrics",
                "sector": cfg.sector_type,
                "tags": ["metrics", ticker.lower()],
            },
        )

    # ── Index de empresa ──────────────────────────────────────────────────────

    def update_company_index(self, ticker: str, info: dict) -> Path:
        """
        Cria/atualiza o arquivo-índice da empresa (03_COMPANIES/{TICKER}/index.md)
        com links para todas as notas existentes da empresa.
        """
        company_dir = self.vault / "03_COMPANIES" / ticker
        company_dir.mkdir(parents=True, exist_ok=True)

        # Listar todas as notas existentes
        notes = sorted(company_dir.glob("*.md"))
        link_lines = [f"- [[{n.stem}]]" for n in notes if n.stem != "index"]

        content = "\n".join(
            [
                f"# {info.get('name', ticker)} ({ticker})",
                f"**Setor**: {info.get('sector', '?')}  |  **Tipo**: {info.get('type', '?')}",
                f"**Atualizado**: {date.today()}",
                "",
                "## Documentos",
                *link_lines,
            ]
        )

        return self.write(
            relative_path=f"03_COMPANIES/{ticker}/index.md",
            content=content,
            frontmatter={
                "ticker": ticker,
                "name": info.get("name", ticker),
                "type": "company-index",
                "updated": str(date.today()),
            },
        )

    # ── Log de outputs ────────────────────────────────────────────────────────

    def _log_output(self, relative_path: str) -> None:
        """Registra o output gerado no log central."""
        log_path = self.vault / "00_META" / "INTELLIGENCE_SYSTEM" / "outputs_log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- `{timestamp}` → [[{Path(relative_path).stem}]] (`{relative_path}`)\n"

        # Criar arquivo se não existir
        if not log_path.exists():
            log_path.write_text(
                "# Intelligence System — Log de Outputs\n\n"
                "Todos os arquivos gerados automaticamente.\n\n",
                encoding="utf-8",
            )

        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)


# ── Helpers de frontmatter ────────────────────────────────────────────────────


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Extrai frontmatter YAML do conteúdo.

    Returns:
        (frontmatter_dict, body_without_frontmatter)
    """
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    try:
        import yaml

        fm_text = content[3:end].strip()
        fm = yaml.safe_load(fm_text) or {}
        body = content[end + 3 :].lstrip("\n")
        return fm, body
    except Exception:
        return {}, content


def _inject_frontmatter(content: str, extra: dict[str, Any]) -> str:
    """
    Mescla frontmatter no conteúdo. Se já existir frontmatter, faz merge.
    Os campos de `extra` têm precedência sobre os existentes.
    """
    if not extra:
        return content

    existing_fm, body = _parse_frontmatter(content)
    merged = {**existing_fm, **extra}  # extra sobrescreve existente

    # Serializar de volta
    try:
        import yaml

        fm_text = yaml.dump(merged, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return f"---\n{fm_text}---\n\n{body}"
    except Exception:
        return content


# ── Instância padrão ──────────────────────────────────────────────────────────

_writer_instance: ObsidianWriter | None = None


def get_writer() -> ObsidianWriter:
    """Retorna instância singleton do ObsidianWriter."""
    global _writer_instance
    if _writer_instance is None:
        _writer_instance = ObsidianWriter()
    return _writer_instance
