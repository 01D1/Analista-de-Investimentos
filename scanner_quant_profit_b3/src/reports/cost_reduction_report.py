"""Relatorio de simulacao de reducao de custos."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df is None or df.empty:
        return "Evidência insuficiente."
    return df[[c for c in cols if c in df.columns]].head(30).to_markdown(index=False)


def generate_cost_reduction_report(base_paper_run_id: int, results_df: pd.DataFrame) -> str:
    results = results_df.copy() if results_df is not None else pd.DataFrame()
    best = results.iloc[0].to_dict() if not results.empty else {}
    rebalance = results[results.get("variant_type", pd.Series(dtype=str)).astype(str).eq("rebalance")] if not results.empty else pd.DataFrame()
    exit_rules = results[results.get("variant_type", pd.Series(dtype=str)).astype(str).eq("exit")] if not results.empty else pd.DataFrame()
    lines = [
        "# Relatório de Simulação de Redução de Custos",
        "",
        "## Baseline",
        f"Paper run base: {base_paper_run_id}.",
        "As variantes são simuladas contra o baseline e não são aplicadas automaticamente.",
        "",
        "## Variantes de rebalanceamento",
        _table(rebalance, ["variant_id", "cost_reduction", "cost_reduction_pct", "return_delta", "drawdown_delta", "turnover_delta", "governance_status"]),
        "",
        "## Variantes de saída",
        _table(exit_rules, ["variant_id", "cost_reduction", "cost_reduction_pct", "return_delta", "drawdown_delta", "turnover_delta", "governance_status"]),
        "",
        "## Comparação antes/depois",
        _table(results, ["variant_id", "variant_type", "cost_drag_total", "entry_cost", "exit_cost", "rebalance_cost", "improvement_score"]),
        "",
        "## Governança",
        f"Melhor variante simulada: {best.get('variant_id', '-')}.",
        f"Status: {best.get('governance_status', '-')}.",
        "",
        "## Trade-offs",
        "Redução de custo só é considerada útil quando não destrói retorno, não aumenta drawdown e não reduz amostra em excesso.",
        "",
        "## Não recomendação",
        "Este relatório não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica variante automaticamente.",
        "",
    ]
    return "\n".join(lines)


def save_cost_reduction_report(path: str | Path, base_paper_run_id: int, results_df: pd.DataFrame) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_cost_reduction_report(base_paper_run_id, results_df), encoding="utf-8")
    return out
