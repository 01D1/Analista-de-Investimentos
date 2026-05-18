"""Relatório Markdown do ranking multi-fonte de hipóteses."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _fmt(value, decimals: int = 4) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


def generate_hypothesis_ranking_markdown(ranked_df: pd.DataFrame, validation_df: pd.DataFrame | None = None) -> str:
    ranked = ranked_df.copy() if ranked_df is not None else pd.DataFrame()
    validation = validation_df.copy() if validation_df is not None else pd.DataFrame()
    best = ranked.iloc[0].to_dict() if not ranked.empty else {}
    lines = [
        "# Relatório de Ranking de Hipóteses",
        "",
        "## Resumo",
        f"Hipóteses ranqueadas: {len(ranked)}.",
        f"Melhor hipótese em estudo: {best.get('hypothesis_id', '-')}.",
        f"Score da melhor hipótese: {_fmt(best.get('hypothesis_robustness_score'), 2)}.",
        "",
        "## Hipóteses testadas",
    ]
    if ranked.empty:
        lines.append("Evidência insuficiente para ranking.")
    else:
        for _, row in ranked.iterrows():
            lines.append(f"- {row.get('hypothesis_id')}: {row.get('hypothesis_class')} / {row.get('governance_status')}")
    lines.extend(["", "## Ranking"])
    if not ranked.empty:
        cols = ["hypothesis_id", "hypothesis_robustness_score", "hypothesis_class", "governance_status", "useful_sources_count", "mean_return_delta", "mean_drawdown_delta", "mean_fragility_delta"]
        lines.append(ranked[[c for c in cols if c in ranked.columns]].to_markdown(index=False))
    lines.extend(["", "## Fontes de sinal"])
    if not validation.empty:
        by_source = validation.groupby("signal_source").agg(rows=("hypothesis_id", "count"), useful_cells=("useful_cells", "sum")).reset_index()
        lines.append(by_source.to_markdown(index=False))
    else:
        lines.append("Sem validação por fonte.")
    lines.extend(["", "## Sensibilidade a custos"])
    if not ranked.empty:
        sensitive = ranked[ranked.get("cost_sensitivity_flag", pd.Series(dtype=bool)).astype(bool)]
        lines.append("Hipóteses sensíveis a custo: " + (", ".join(sensitive["hypothesis_id"].astype(str).tolist()) if not sensitive.empty else "nenhuma no ranking salvo."))
    lines.extend(["", "## Overfitting"])
    if not ranked.empty:
        overfit = ranked[ranked.get("overfitting_flag", pd.Series(dtype=bool)).astype(bool)]
        lines.append("Hipóteses com flag de overfitting: " + (", ".join(overfit["hypothesis_id"].astype(str).tolist()) if not overfit.empty else "nenhuma no ranking salvo."))
    lines.extend(["", "## Governança"])
    if not ranked.empty:
        gov = ranked["governance_status"].value_counts().rename_axis("governance_status").reset_index(name="count")
        lines.append(gov.to_markdown(index=False))
    lines.extend(
        [
            "",
            "## Próximos testes",
            "- Repetir o ranking com cenários de custo e regimes ativos.",
            "- Aumentar janelas OOS antes de promover qualquer hipótese robusta para observação recorrente.",
            "- Investigar hipóteses bloqueadas por baixa cobertura, custo ou overfitting.",
            "",
            "## Não recomendação",
            "Este relatório é simulação, investigação e validação. Não executa ordens reais, não recomenda compra/venda e não aplica hipóteses automaticamente.",
            "",
        ]
    )
    return "\n".join(lines)


def save_hypothesis_ranking_markdown(path: str | Path, ranked_df: pd.DataFrame, validation_df: pd.DataFrame | None = None) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_hypothesis_ranking_markdown(ranked_df, validation_df), encoding="utf-8")
    return out

