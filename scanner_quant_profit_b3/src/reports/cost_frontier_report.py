"""Relatório da fronteira custo-retorno-drawdown."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df is None or df.empty:
        return "Evidência insuficiente."
    return df[[c for c in cols if c in df.columns]].head(30).to_markdown(index=False)


def generate_cost_frontier_report(cost_reduction_run_id: int, results_df: pd.DataFrame) -> str:
    results = results_df.copy() if results_df is not None else pd.DataFrame()
    efficient = results[results.get("is_efficient", pd.Series(dtype=bool)).astype(bool)] if not results.empty else pd.DataFrame()
    dominated = results[~results.get("is_efficient", pd.Series(dtype=bool)).astype(bool)] if not results.empty else pd.DataFrame()
    best = results.iloc[0].to_dict() if not results.empty else {}
    lines = [
        "# Relatório de Fronteira Custo-Retorno-Drawdown",
        "",
        "## Resumo",
        f"Run de redução de custo analisado: {cost_reduction_run_id}.",
        f"Variantes analisadas: {len(results)}.",
        f"Variantes na fronteira eficiente: {len(efficient)}.",
        "",
        "## Variantes analisadas",
        _table(results, ["variant_id", "variant_type", "cost_reduction_pct", "return_delta", "drawdown_delta", "turnover_delta", "tradeoff_score", "governance_status"]),
        "",
        "## Fronteira eficiente",
        _table(efficient, ["frontier_rank", "variant_id", "tradeoff_score", "tradeoff_class", "cost_reduction_pct", "return_delta", "drawdown_delta", "governance_status"]),
        "",
        "## Trade-offs",
        _table(results, ["variant_id", "cost_reduction_to_return_loss", "cost_reduction_to_drawdown_penalty", "efficiency_score", "tradeoff_class"]),
        "",
        "## Governança",
        f"Melhor trade-off em estudo: {best.get('variant_id', '-')}.",
        f"Status: {best.get('governance_status', '-')}.",
        "",
        "## Conclusão",
        "A fronteira eficiente mostra variantes não dominadas, mas aprovação exige preservar retorno, controlar drawdown e manter amostra suficiente.",
        "",
        "## Variantes dominadas",
        _table(dominated, ["variant_id", "dominated_by", "efficiency_reason"]),
        "",
        "## Não recomendação",
        "Este relatório não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica variante automaticamente.",
        "",
    ]
    return "\n".join(lines)


def save_cost_frontier_report(path: str | Path, cost_reduction_run_id: int, results_df: pd.DataFrame) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_cost_frontier_report(cost_reduction_run_id, results_df), encoding="utf-8")
    return out
