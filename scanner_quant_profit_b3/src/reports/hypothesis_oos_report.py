"""Relatorio markdown de validacao OOS de hipoteses."""
from __future__ import annotations

import json

import pandas as pd


def _fmt(value, decimals: int = 4) -> str:
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, (int, float)):
        return f"{float(value):.{decimals}f}"
    return str(value)


def _metadata(row) -> dict:
    raw = row.get("metadata_json", "{}") if hasattr(row, "get") else "{}"
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}


def generate_hypothesis_oos_report(run_summary: dict | pd.Series, results_df: pd.DataFrame, coverage_df: pd.DataFrame | None = None) -> str:
    summary = run_summary.to_dict() if isinstance(run_summary, pd.Series) else dict(run_summary or {})
    meta = _metadata(summary)
    hypothesis = meta.get("hypothesis", {}) if isinstance(meta, dict) else {}
    governance = meta.get("governance", {}) if isinstance(meta, dict) else {}
    lines = [
        "# Relatorio OOS da Hipotese",
        "",
        "Este relatorio avalia uma hipotese de investigacao em simulacao OOS/multi-cenario. Nao executa ordens reais, nao recomenda compra/venda e nao aplica a hipotese automaticamente.",
        "",
        "## Hipotese",
        f"- ID: {summary.get('hypothesis_id', hypothesis.get('hypothesis_id', '-'))}",
        f"- Tipo: {summary.get('hypothesis_type', hypothesis.get('hypothesis_type', '-'))}",
        f"- Alvo: {summary.get('target', hypothesis.get('target', '-'))}",
        "",
        "## Cenarios",
        f"- Cenarios testados: {summary.get('scenarios_count', '-')}",
        f"- Janelas OOS: {summary.get('windows_count', '-')}",
        "",
        "## Comparacao vs Baseline",
        f"- Melhora positiva: {_fmt(summary.get('positive_improvement_pct'))}",
        f"- Delta medio de retorno: {_fmt(summary.get('mean_return_delta'))}",
        f"- Delta medio de drawdown: {_fmt(summary.get('mean_drawdown_delta'))}",
        f"- Delta medio de fragilidade: {_fmt(summary.get('mean_fragility_delta'))}",
        f"- Robustez: {summary.get('robustness_class', '-')}",
        "",
        "## Sensibilidade a Custo",
        f"- Percentual com flag de custo/slippage: {_fmt(meta.get('cost_sensitive_pct', summary.get('cost_sensitive_pct')) if isinstance(meta, dict) else summary.get('cost_sensitive_pct'))}",
        "",
        "## Cobertura OOS",
    ]
    coverage_summary = meta.get("coverage_summary", {}) if isinstance(meta, dict) else {}
    coverage_comparison = meta.get("coverage_comparison", {}) if isinstance(meta, dict) else {}
    if coverage_summary:
        lines.extend(
            [
                f"- Células úteis: {coverage_summary.get('useful_cells', '-')}/{coverage_summary.get('coverage_cells', '-')}",
                f"- Percentual útil: {_fmt(coverage_summary.get('useful_cells_pct'))}",
                f"- Fontes com dados úteis: {coverage_summary.get('sources_with_useful_data', '-')}",
                f"- Regimes com dados úteis: {coverage_summary.get('regimes_with_useful_data', '-')}",
                f"- Status: {coverage_summary.get('coverage_status', '-')}",
            ]
        )
    if coverage_comparison:
        lines.extend(
            [
                f"- Antes/depois células úteis: {coverage_comparison.get('before_useful_cells', '-')} -> {coverage_comparison.get('after_useful_cells', '-')}",
                f"- Delta percentual útil: {_fmt(coverage_comparison.get('useful_cells_pct_delta'))}",
            ]
        )
    if coverage_df is not None and not coverage_df.empty:
        missing = coverage_df[~coverage_df["useful_cell"].astype(bool)].head(8)
        if not missing.empty:
            lines.append("- Principais células sem dados úteis:")
            for _, row in missing.iterrows():
                lines.append(f"  - {row.get('scenario_name')} / {row.get('signal_source')} / {row.get('regime_filter') or 'sem_regime'}: {row.get('source_coverage_status')}")
    lines.extend(
        [
            "",
            "## Regimes",
            f"- Percentual com instabilidade por regime: {_fmt(meta.get('regime_instability_pct', summary.get('regime_instability_pct')) if isinstance(meta, dict) else summary.get('regime_instability_pct'))}",
            "",
            "## Governanca",
            f"- Status: {summary.get('governance_status', governance.get('governance_status', '-'))}",
        ]
    )
    if governance:
        for label, values in [("Motivos favoraveis", governance.get("reasons_for", [])), ("Motivos contrarios", governance.get("reasons_against", [])), ("Acoes necessarias", governance.get("required_actions", []))]:
            lines.append(f"- {label}:")
            if values:
                lines.extend([f"  - {item}" for item in values])
            else:
                lines.append("  - Nenhum item registrado.")

    lines.extend(["", "## Janelas"])
    if results_df is None or results_df.empty:
        lines.append("- Dados insuficientes para listar janelas.")
    else:
        cols = ["window_id", "scenario_name", "return_delta", "drawdown_delta", "fragility_delta", "trades_count", "improvement_detected", "overfitting_flag", "cost_sensitivity_flag", "regime_instability_flag"]
        for _, row in results_df[[c for c in cols if c in results_df.columns]].head(20).iterrows():
            lines.append(
                f"- Janela {row.get('window_id')} / {row.get('scenario_name')}: "
                f"delta retorno {_fmt(row.get('return_delta'))}, "
                f"delta drawdown {_fmt(row.get('drawdown_delta'))}, "
                f"delta fragilidade {_fmt(row.get('fragility_delta'))}, "
                f"trades {int(row.get('trades_count') or 0)}"
            )

    lines.extend(
        [
            "",
            "## Conclusao",
            "Hipoteses aprovadas nesta etapa continuam sendo hipoteses em validacao. A promocao para observacao recorrente exige acompanhamento em novos periodos.",
            "",
            "## Nao recomendacao",
            "Este relatorio e simulado e analitico. Nao constitui recomendacao financeira e nao autoriza execucao real.",
        ]
    )
    return "\n".join(lines) + "\n"
