"""Relatorio da validacao multi-cenario do paper trading."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame | None, limit: int = 30) -> str:
    if df is None or df.empty:
        return "_Sem dados salvos._"
    return df.head(limit).to_markdown(index=False)


def _metadata(row: dict) -> dict:
    try:
        return json.loads(row.get("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def generate_paper_scenario_validation_report(
    run_summary: dict | None = None,
    results_df: pd.DataFrame | None = None,
    cost_df: pd.DataFrame | None = None,
    source_df: pd.DataFrame | None = None,
    regime_df: pd.DataFrame | None = None,
) -> str:
    run = run_summary or {}
    meta = _metadata(run)
    governance = meta.get("governance", {})
    summary = meta.get("summary", {})
    return f"""# Relatorio de Validacao Multi-Cenario

## Resumo

- Status: {run.get("status", "-")}
- Governanca: {run.get("governance_status", "-")}
- Periodos: {run.get("periods_count", 0)}
- Cenarios: {run.get("scenarios_count", 0)}
- Fontes de sinal: {run.get("signal_sources_count", 0)}
- Retorno medio: {run.get("mean_return", 0)}
- Drawdown medio: {run.get("mean_drawdown", 0)}
- Periodos positivos: {run.get("positive_periods_pct", 0)}
- Robustez: {summary.get("robustness", "-")}

## Periodos Testados

{_table(results_df)}

## Cenarios de Custo

{_table(cost_df)}

## Fontes de Sinal

{_table(source_df)}

## Regimes

{_table(regime_df)}

## Governanca

- Motivos favoraveis: {", ".join(governance.get("reasons_for", []) or []) or "-"}
- Motivos contrarios: {", ".join(governance.get("reasons_against", []) or []) or "-"}
- Acoes necessarias: {", ".join(governance.get("required_actions", []) or []) or "-"}

## Conclusao Analitica

A validacao multi-cenario separa melhora pontual de robustez observada em diferentes periodos, custos, fontes de sinal e regimes. Qualquer parametro permanece em estudo quando houver baixa amostra, sensibilidade a custos, fragilidade por regime ou evidencia de overfitting.

## Nao Recomendacao

Este relatorio e apenas simulacao. Nao executa ordens reais, nao recomenda compra ou venda, nao altera score principal e nao aplica parametros automaticamente.
"""


def save_paper_scenario_validation_report(
    output_dir: str | Path,
    run_summary: dict | None = None,
    results_df: pd.DataFrame | None = None,
    cost_df: pd.DataFrame | None = None,
    source_df: pd.DataFrame | None = None,
    regime_df: pd.DataFrame | None = None,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "paper_scenario_validation_report.md"
    path.write_text(generate_paper_scenario_validation_report(run_summary, results_df, cost_df, source_df, regime_df), encoding="utf-8")
    return path
