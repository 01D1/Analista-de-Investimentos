"""Relatório Markdown da calibração LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df is None or df.empty:
        return "Evidência insuficiente."
    return df[[c for c in cols if c in df.columns]].to_markdown(index=False)


def generate_limit_signal_source_markdown(ranked_df: pd.DataFrame, oos_df: pd.DataFrame | None = None, variants_df: pd.DataFrame | None = None) -> str:
    ranked = ranked_df.copy() if ranked_df is not None else pd.DataFrame()
    oos = oos_df.copy() if oos_df is not None else pd.DataFrame()
    variants = variants_df.copy() if variants_df is not None else pd.DataFrame()
    best = ranked.iloc[0].to_dict() if not ranked.empty else {}
    lines = [
        "# Relatório de Calibração — LIMIT_SIGNAL_SOURCE",
        "",
        "## Resumo",
        f"Variações ranqueadas: {len(ranked)}.",
        f"Melhor variação paramétrica em estudo: {best.get('variant_id', '-')}.",
        f"Governança da melhor variação: {best.get('governance_status', '-')}.",
        "",
        "## Variações testadas",
        _table(variants, ["variant_id", "target_source", "cost_limit", "slippage_limit", "required_confirmations", "overfitting_risk"]),
        "",
        "## Custo e slippage",
        _table(ranked, ["variant_id", "mean_cost_drag_delta", "mean_slippage_delta", "cost_sensitivity_flag", "slippage_sensitivity_flag"]),
        "",
        "## Fontes de sinal",
        _table(oos, ["variant_id", "signal_source", "positive_improvement_pct", "mean_return_delta", "mean_fragility_delta"]),
        "",
        "## Regimes",
        _table(oos, ["variant_id", "regime", "positive_improvement_pct", "removed_pct"]),
        "",
        "## Ranking",
        _table(ranked, ["variant_id", "variant_robustness_score", "variant_class", "governance_status", "removed_pct", "mean_return_delta", "mean_fragility_delta"]),
        "",
        "## Governança",
        _table(ranked, ["variant_id", "governance_status", "overfitting_flag", "low_sample_flag"]),
        "",
        "## Conclusão",
        "A calibração é uma hipótese em estudo. Variações bloqueadas por governança exigem nova investigação antes de qualquer observação recorrente.",
        "",
        "## Não recomendação",
        "Este relatório não executa ordens reais, não recomenda compra/venda, não altera score principal, não altera ranking principal e não aplica variações automaticamente.",
        "",
    ]
    return "\n".join(lines)


def save_limit_signal_source_markdown(path: str | Path, ranked_df: pd.DataFrame, oos_df: pd.DataFrame | None = None, variants_df: pd.DataFrame | None = None) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_limit_signal_source_markdown(ranked_df, oos_df, variants_df), encoding="utf-8")
    return out
