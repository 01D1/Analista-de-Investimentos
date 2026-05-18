"""Comparacao formal entre simulacao simples e avancada de paper trading."""
from __future__ import annotations

import math

import pandas as pd


METRICS = [
    "capital_final",
    "total_return",
    "sharpe",
    "sortino",
    "max_drawdown",
    "trades_count",
    "win_rate",
    "profit_factor",
    "turnover",
    "exposure_avg",
    "var_avg",
    "es_avg",
    "governance_status",
]

LOWER_IS_BETTER = {"max_drawdown", "var_avg", "es_avg"}
CONTROLLED_IS_BETTER = {"turnover", "trades_count", "exposure_avg"}


def _as_float(value):
    try:
        if value is None or value == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _is_material(metric: str, simple_value, advanced_value, delta) -> bool:
    if metric == "governance_status":
        return str(simple_value) != str(advanced_value)
    if pd.isna(delta):
        return False
    if metric in {"total_return", "max_drawdown", "win_rate"}:
        return abs(float(delta)) >= 0.01
    if metric in {"sharpe", "sortino", "profit_factor"}:
        return abs(float(delta)) >= 0.20
    if metric in {"capital_final", "trades_count", "turnover"}:
        return abs(float(delta)) >= max(abs(_as_float(simple_value)) * 0.05, 1.0)
    return abs(float(delta)) > 0


def _improved(metric: str, simple_value, advanced_value, delta) -> bool:
    if metric == "governance_status":
        adv = str(advanced_value or "").upper()
        simple = str(simple_value or "").upper()
        return "BLOCKED" not in adv and adv != simple
    if pd.isna(delta):
        return False
    if metric in LOWER_IS_BETTER:
        return abs(_as_float(advanced_value)) < abs(_as_float(simple_value))
    if metric in CONTROLLED_IS_BETTER:
        simple = _as_float(simple_value)
        advanced = _as_float(advanced_value)
        if metric == "trades_count":
            return advanced >= 10 and advanced >= simple
        return advanced <= max(simple * 1.25, simple + 5)
    return float(delta) > 0


def compare_paper_simulations(simple_summary: dict | pd.Series, advanced_summary: dict | pd.Series) -> pd.DataFrame:
    """Compara metricas chave de duas simulacoes paper.

    A comparacao e analitica: ela nao recomenda parametros e nao altera regras.
    """
    simple = dict(simple_summary) if simple_summary is not None else {}
    advanced = dict(advanced_summary) if advanced_summary is not None else {}
    rows = []
    for metric in METRICS:
        simple_value = simple.get(metric)
        advanced_value = advanced.get(metric)
        simple_num = _as_float(simple_value)
        advanced_num = _as_float(advanced_value)
        delta = advanced_num - simple_num if pd.notna(simple_num) and pd.notna(advanced_num) else pd.NA
        rows.append(
            {
                "metric": metric,
                "simple_value": simple_value,
                "advanced_value": advanced_value,
                "delta": delta,
                "improved": _improved(metric, simple_value, advanced_value, delta),
                "material_change": _is_material(metric, simple_value, advanced_value, delta),
            }
        )
    return pd.DataFrame(rows, columns=["metric", "simple_value", "advanced_value", "delta", "improved", "material_change"])


def generate_simulation_comparison_report(comparison_df: pd.DataFrame) -> str:
    if comparison_df is None or comparison_df.empty:
        return "Comparacao indisponivel: dados insuficientes para comparar simple vs advanced."
    improved = comparison_df[comparison_df["improved"] == True]["metric"].astype(str).tolist()
    material = comparison_df[comparison_df["material_change"] == True]["metric"].astype(str).tolist()
    warnings = []
    turnover = comparison_df[comparison_df["metric"] == "turnover"]
    if not turnover.empty and pd.to_numeric(turnover["delta"], errors="coerce").fillna(0).iloc[0] > 0:
        warnings.append("aumentou o numero de ordens simuladas")
    drawdown = comparison_df[comparison_df["metric"] == "max_drawdown"]
    if not drawdown.empty and not bool(drawdown["improved"].iloc[0]):
        warnings.append("nao reduziu drawdown simulado")
    text = [
        "A comparacao simple vs advanced e apenas uma leitura de simulacao.",
        f"Metricas com melhora: {', '.join(improved) if improved else 'nenhuma melhora material'}."
        f" Mudancas materiais: {', '.join(material) if material else 'sem mudanca material'}."
    ]
    if warnings:
        text.append("Pontos de atencao: " + "; ".join(warnings) + ".")
    text.append("Os parametros permanecem em estudo e devem ser avaliados fora da amostra antes de qualquer uso.")
    return " ".join(text)
