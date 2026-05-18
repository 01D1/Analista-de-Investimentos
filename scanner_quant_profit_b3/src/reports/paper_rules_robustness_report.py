"""Relatorio de robustez das regras simuladas de paper trading."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _fmt(value, decimals: int = 4) -> str:
    try:
        if pd.isna(value):
            return "-"
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value if value is not None else "-")


def _table(df: pd.DataFrame, limit: int = 20) -> str:
    if df is None or df.empty:
        return "_Sem dados salvos._"
    return df.head(limit).to_markdown(index=False)


def generate_paper_rules_robustness_report(
    comparison_df: pd.DataFrame | None = None,
    optimization_df: pd.DataFrame | None = None,
    wf_results_df: pd.DataFrame | None = None,
    wf_summary: dict | None = None,
    governance_review: dict | None = None,
) -> str:
    summary = wf_summary or {}
    governance = governance_review or {}
    best_params = "-"
    if optimization_df is not None and not optimization_df.empty and "params_json" in optimization_df.columns:
        best_params = str(optimization_df.iloc[0]["params_json"])
    return f"""# Relatorio de Robustez das Regras de Paper Trading

## Comparacao Simple vs Advanced

{_table(comparison_df)}

## Otimizacao de Parametros

- Melhor parametro em estudo: {best_params}
- A otimizacao e exploratoria e nao aplica parametros automaticamente.

{_table(optimization_df)}

## Walk-forward

- Janelas: {summary.get("windows_count", 0)}
- Janelas positivas: {_fmt(summary.get("positive_windows_pct"))}
- Retorno medio OOS: {_fmt(summary.get("mean_test_return"))}
- Drawdown medio OOS: {_fmt(summary.get("mean_test_drawdown"))}
- Profit factor medio OOS: {_fmt(summary.get("mean_test_profit_factor"))}
- Robustez: {summary.get("robustness_class", "PAPER_WF_DADOS_INSUFICIENTES")}

{_table(wf_results_df)}

## Governanca OOS

- Status: {governance.get("governance_status", "-")}
- Motivos favoraveis: {", ".join(governance.get("reasons_for", []) or []) or "-"}
- Motivos contrarios: {", ".join(governance.get("reasons_against", []) or []) or "-"}
- Acoes necessarias: {", ".join(governance.get("required_actions", []) or []) or "-"}

## Limitacoes

- Resultados dependem da qualidade dos sinais, precos, custos e snapshots de risco disponiveis.
- Regras simuladas podem estar superajustadas ao periodo de treino.
- Parametros devem permanecer como estudo enquanto a robustez OOS for insuficiente.

## Nao recomendacao

Este relatorio descreve apenas simulacao e analise de regras. Nao executa ordens reais, nao recomenda compra ou venda e nao altera score ou ranking principal.
"""


def save_paper_rules_robustness_report(
    output_dir: str | Path,
    comparison_df: pd.DataFrame | None = None,
    optimization_df: pd.DataFrame | None = None,
    wf_results_df: pd.DataFrame | None = None,
    wf_summary: dict | None = None,
    governance_review: dict | None = None,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "paper_rules_robustness_report.md"
    path.write_text(
        generate_paper_rules_robustness_report(comparison_df, optimization_df, wf_results_df, wf_summary, governance_review),
        encoding="utf-8",
    )
    return path
