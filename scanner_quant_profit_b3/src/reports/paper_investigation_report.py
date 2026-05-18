"""Relatorio markdown das investigacoes de fragilidade do paper trading."""
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


def generate_paper_investigation_report(run_summary: dict | pd.Series, hypotheses_df: pd.DataFrame, results_df: pd.DataFrame) -> str:
    summary = run_summary.to_dict() if isinstance(run_summary, pd.Series) else dict(run_summary or {})
    lines = [
        "# Relatorio de Investigacoes da Carteira Simulada",
        "",
        "Este relatorio descreve hipoteses de investigacao e experimentos simulados. Nao executa ordens reais, nao recomenda compra/venda e nao altera score ou ranking.",
        "",
        "## Resumo",
        f"- Paper run base: {summary.get('base_paper_run_id', '-')}",
        f"- Fragility run base: {summary.get('base_fragility_run_id', '-')}",
        f"- Hipoteses geradas: {summary.get('hypotheses_count', len(hypotheses_df) if hypotheses_df is not None else 0)}",
        f"- Hipoteses com melhora: {summary.get('improved_count', '-')}",
        f"- Melhor hipotese: {summary.get('best_hypothesis_id', '-')}",
        f"- Melhor improvement_score: {_fmt(summary.get('best_improvement_score'), 2)}",
        "",
        "## Fragilidades Detectadas",
    ]
    meta = _metadata(summary)
    base = meta.get("base", {}) if isinstance(meta, dict) else {}
    if base:
        lines.extend(
            [
                f"- Fragility score base: {_fmt(base.get('fragility_score'), 2)}",
                f"- Retorno base: {_fmt(base.get('total_return'))}",
                f"- Drawdown base: {_fmt(base.get('max_drawdown'))}",
                f"- Cost drag base: {_fmt(base.get('cost_drag'), 2)}",
            ]
        )
    else:
        lines.append("- Base de fragilidade nao informada no resumo.")

    lines.extend(["", "## Hipoteses Geradas"])
    if hypotheses_df is None or hypotheses_df.empty:
        lines.append("- Nenhuma hipotese de investigacao foi gerada.")
    else:
        for _, row in hypotheses_df.head(20).iterrows():
            lines.append(f"- {row.get('hypothesis_id')}: {row.get('title')} ({row.get('hypothesis_type')} / alvo {row.get('target')})")

    lines.extend(["", "## Simulacoes Alternativas"])
    if results_df is None or results_df.empty:
        lines.append("- Nenhum experimento simulado foi executado.")
    else:
        cols = ["hypothesis_id", "simulated_return", "simulated_drawdown", "simulated_trades", "fragility_score_after", "improvement_score", "governance_status"]
        for _, row in results_df.sort_values("improvement_score", ascending=False).head(15).iterrows():
            lines.append(
                "- "
                + ", ".join(
                    [
                        str(row.get("hypothesis_id")),
                        f"retorno {_fmt(row.get('simulated_return'))}",
                        f"drawdown {_fmt(row.get('simulated_drawdown'))}",
                        f"trades {int(row.get('simulated_trades') or 0)}",
                        f"fragility_after {_fmt(row.get('fragility_score_after'), 2)}",
                        f"score {_fmt(row.get('improvement_score'), 2)}",
                        str(row.get("governance_status")),
                    ]
                )
            )

    lines.extend(
        [
            "",
            "## Comparacao Antes/Depois",
            "As comparacoes medem apenas experimentos simulados. Melhoras que reduzem demais a amostra permanecem em observacao por risco de overfitting.",
            "",
            "## Trade-offs",
        ]
    )
    if results_df is not None and not results_df.empty:
        warnings = []
        for _, row in results_df.iterrows():
            meta_row = _metadata(row)
            comparison = meta_row.get("comparison", {}) if isinstance(meta_row, dict) else {}
            for key in ["tradeoff_warning", "overfitting_warning"]:
                if comparison.get(key):
                    warnings.append(f"- {row.get('hypothesis_id')}: {comparison[key]}")
        lines.extend(warnings or ["- Nenhum trade-off relevante registrado nos metadados."])
    else:
        lines.append("- Dados insuficientes para avaliar trade-offs.")

    lines.extend(
        [
            "",
            "## Governanca das Hipoteses",
            "Hipoteses aprovadas aqui sao apenas aprovadas para novo teste, preferencialmente multi-cenario e fora da amostra.",
            "",
            "## Proximos Testes",
            "- Repetir as hipoteses promissoras em validacao multi-cenario.",
            "- Verificar sensibilidade a custos e slippage antes de qualquer interpretacao.",
            "- Confirmar que a melhora nao depende de remover amostra demais.",
            "",
            "## Nao recomendacao",
            "Este relatorio e analitico e simulado. Nao constitui recomendacao financeira e nao autoriza execucao real.",
        ]
    )
    return "\n".join(lines) + "\n"
