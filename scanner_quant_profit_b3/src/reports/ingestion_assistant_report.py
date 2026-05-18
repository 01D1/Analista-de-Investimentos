"""Relatorio Markdown do assistente de ingestao."""
from __future__ import annotations

import pandas as pd


def _table(df: pd.DataFrame, columns: list[str]) -> str:
    if df is None or df.empty:
        return "_Sem dados._"
    cols = [c for c in columns if c in df.columns]
    return df[cols].to_markdown(index=False)


def generate_ingestion_assistant_report(run_summary: dict, steps_df: pd.DataFrame, validation_df: pd.DataFrame, comparison_df: pd.DataFrame) -> str:
    return "\n\n".join(
        [
            "# Relatório do Assistente de Ingestão",
            "## 1. Resumo\n"
            f"- Status: {run_summary.get('status', '-')}\n"
            f"- Dry-run: {run_summary.get('dry_run', True)}\n"
            f"- Fontes: {run_summary.get('sources', '-')}\n"
            f"- Etapas: {run_summary.get('steps_total', 0)}\n"
            f"- Melhorias detectadas: {run_summary.get('improvements_count', 0)}",
            "## 2. Plano de Ingestão\n" + _table(steps_df, ["step_order", "source_domain", "step_type", "title", "suggested_command", "risk_level", "status"]),
            "## 3. Execução\n" + _table(steps_df, ["step_order", "source_domain", "status", "stderr"]),
            "## 4. Validação Pós-processamento\n" + _table(validation_df, ["source_domain", "validation_status", "records_before", "records_after", "message"]),
            "## 5. Comparação Antes/Depois\n" + _table(comparison_df, ["source_name", "before_score", "after_score", "score_delta", "before_status", "after_status", "message"]),
            "## 6. Próximas ações\nRevisar etapas manuais, fontes ainda stale e comandos sugeridos. Este relatório é operacional e não constitui recomendação.",
        ]
    )

