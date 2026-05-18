"""Relatorio Markdown do deep dive de hipoteses."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _fmt(value, decimals: int = 4) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df is None or df.empty:
        return "Evidencia insuficiente."
    selected = df[[c for c in cols if c in df.columns]]
    if selected.empty:
        return "Evidencia insuficiente."
    return selected.to_markdown(index=False)


def _flagged(df: pd.DataFrame, flag_col: str) -> pd.DataFrame:
    if df is None or df.empty or flag_col not in df.columns:
        return pd.DataFrame()
    return df[df[flag_col].astype(bool)].copy()


def generate_hypothesis_deep_dive_markdown(
    deep_oos_df: pd.DataFrame,
    block_reasons_df: pd.DataFrame | None = None,
    asset_decomposition_df: pd.DataFrame | None = None,
    source_decomposition_df: pd.DataFrame | None = None,
) -> str:
    deep = deep_oos_df.copy() if deep_oos_df is not None else pd.DataFrame()
    reasons = block_reasons_df.copy() if block_reasons_df is not None else pd.DataFrame()
    assets = asset_decomposition_df.copy() if asset_decomposition_df is not None else pd.DataFrame()
    sources = source_decomposition_df.copy() if source_decomposition_df is not None else pd.DataFrame()
    hypotheses = sorted(deep.get("hypothesis_id", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    lines = [
        "# Relatório Deep Dive de Hipóteses",
        "",
        "## Resumo",
        f"Hipóteses analisadas: {len(hypotheses)}.",
        f"Linhas OOS profundas: {len(deep)}.",
        "Esta camada é uma simulação de hipótese em estudo, sem recomendação e sem execução de ordens reais.",
        "",
        "## Hipóteses analisadas",
        ", ".join(hypotheses) if hypotheses else "Evidência insuficiente.",
        "",
        "## Resultado OOS profundo",
    ]
    if not deep.empty:
        agg = (
            deep.groupby("hypothesis_id")
            .agg(
                positive_improvement_pct=("positive_improvement_pct", "mean"),
                mean_return_delta=("mean_return_delta", "mean"),
                mean_drawdown_delta=("mean_drawdown_delta", "mean"),
                mean_fragility_delta=("mean_fragility_delta", "mean"),
                trades_count=("trades_count", "sum"),
                governance_status=("governance_status", "first"),
            )
            .reset_index()
        )
        lines.append(agg.to_markdown(index=False))
    else:
        lines.append("Evidência insuficiente para deep dive.")
    lines.extend(
        [
            "",
            "## Sensibilidade a custo",
            _table(_flagged(deep, "cost_sensitivity_flag"), ["hypothesis_id", "signal_source", "cost_scenario", "mean_return_delta", "block_reason"]),
            "",
            "## Sensibilidade a slippage",
            _table(_flagged(deep, "slippage_sensitivity_flag"), ["hypothesis_id", "signal_source", "slippage_scenario", "mean_return_delta", "block_reason"]),
            "",
            "## Regimes",
            _table(deep, ["hypothesis_id", "signal_source", "regime", "positive_improvement_pct", "mean_return_delta", "mean_fragility_delta", "block_reason"]),
            "",
            "## Ativos",
            _table(assets, ["hypothesis_id", "ticker", "trades_count", "mean_return_delta", "mean_fragility_delta", "contribution_to_blockage", "asset_classification"]),
            "",
            "## Fontes de sinal",
            _table(sources, ["hypothesis_id", "source", "positive_improvement_pct", "mean_return_delta", "mean_fragility_delta", "block_reason", "source_classification"]),
            "",
            "## Motivos de bloqueio",
            _table(reasons, ["hypothesis_id", "primary_block_reason", "secondary_block_reason", "explanation"]),
            "",
            "## Governança",
        ]
    )
    if not deep.empty and "governance_status" in deep.columns:
        gov = deep[["hypothesis_id", "governance_status"]].drop_duplicates()
        lines.append(gov.to_markdown(index=False))
    else:
        lines.append("Evidência insuficiente.")
    lines.extend(
        [
            "",
            "## Próximos testes",
            "- Investigar ajustes apenas onde a hipotese reduziu fragilidade sem destruir retorno.",
            "- Repetir em janelas mais longas antes de qualquer observacao recorrente.",
            "- Separar condicoes de fragilidade por custo, slippage, regime, fonte e ativo.",
            "",
            "## Não recomendação",
            "Este relatorio e uma validacao analitica. Nao executa ordens reais, nao recomenda compra/venda, nao altera ranking principal e nao aplica hipoteses automaticamente.",
            "",
        ]
    )
    return "\n".join(lines)


def save_hypothesis_deep_dive_markdown(
    path: str | Path,
    deep_oos_df: pd.DataFrame,
    block_reasons_df: pd.DataFrame | None = None,
    asset_decomposition_df: pd.DataFrame | None = None,
    source_decomposition_df: pd.DataFrame | None = None,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        generate_hypothesis_deep_dive_markdown(deep_oos_df, block_reasons_df, asset_decomposition_df, source_decomposition_df),
        encoding="utf-8",
    )
    return out
