"""Ranking multi-fonte de hipóteses em estudo."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.hypothesis_ranking_governance import evaluate_ranked_hypothesis


RANKING_COLUMNS = [
    "hypothesis_id",
    "signal_source",
    "scenario_name",
    "windows_count",
    "useful_cells",
    "useful_sources_count",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "mean_cost_drag_delta",
    "improvement_consistency_score",
    "return_delta_score",
    "drawdown_reduction_score",
    "fragility_reduction_score",
    "cost_robustness_score",
    "source_diversity_score",
    "regime_stability_score",
    "overfitting_penalty",
    "data_coverage_penalty",
    "cost_sensitivity_flag",
    "overfitting_flag",
    "regime_instability_flag",
    "hypothesis_robustness_score",
    "hypothesis_class",
    "governance_status",
    "metadata_json",
]


def _scale(value: float, good_at: float, bad_at: float = 0.0, reverse: bool = False) -> float:
    if reverse:
        value = -value
    if good_at == bad_at:
        return 0.0
    score = (value - bad_at) / (good_at - bad_at) * 100
    return float(max(0, min(100, score)))


def _classification(score: float, positive: float, ret: float, frag: float, overfit: bool, coverage_penalty: float) -> str:
    if coverage_penalty >= 50:
        return "HYPOTHESIS_INSUFFICIENT_DATA"
    if score >= 75 and positive >= 0.55 and ret >= 0 and frag < 0 and not overfit:
        return "HYPOTHESIS_ROBUST"
    if score >= 60 and frag < 0 and positive >= 0.45:
        return "HYPOTHESIS_PROMISING"
    if score >= 45 and frag <= 0:
        return "HYPOTHESIS_OBSERVATION_ONLY"
    if score >= 30:
        return "HYPOTHESIS_FRAGILE"
    return "HYPOTHESIS_REJECTED"


def rank_hypotheses(validation_df: pd.DataFrame) -> pd.DataFrame:
    if validation_df is None or validation_df.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)
    rows = []
    df = validation_df.copy()
    for hypothesis_id, group in df.groupby("hypothesis_id", dropna=False):
        useful = group[group["data_coverage_status"].astype(str).isin(["COVERAGE_USEFUL", "COBERTURA_BOA", "COVERAGE_REQUIREMENTS_PASS"])].copy()
        base = useful if not useful.empty else group
        positive = float(pd.to_numeric(base["positive_improvement_pct"], errors="coerce").fillna(0).mean())
        ret = float(pd.to_numeric(base["mean_return_delta"], errors="coerce").fillna(0).mean())
        drawdown = float(pd.to_numeric(base["mean_drawdown_delta"], errors="coerce").fillna(0).mean())
        frag = float(pd.to_numeric(base["mean_fragility_delta"], errors="coerce").fillna(0).mean())
        cost_drag = float(pd.to_numeric(base["mean_cost_drag_delta"], errors="coerce").fillna(0).mean())
        overfit_pct = float(base["overfitting_flag"].astype(bool).mean()) if "overfitting_flag" in base else 0.0
        cost_pct = float(base["cost_sensitivity_flag"].astype(bool).mean()) if "cost_sensitivity_flag" in base else 0.0
        regime_pct = float(base["regime_instability_flag"].astype(bool).mean()) if "regime_instability_flag" in base else 0.0
        useful_sources = int(useful["signal_source"].nunique()) if not useful.empty else 0
        total_sources = max(1, int(group["signal_source"].nunique()))
        coverage_ratio = float(len(useful) / len(group)) if len(group) else 0.0

        improvement_score = positive * 100
        return_score = _scale(ret, good_at=0.01, bad_at=-0.01)
        drawdown_score = _scale(drawdown, good_at=0.02, bad_at=-0.02)
        fragility_score = _scale(frag, good_at=20, bad_at=0, reverse=True)
        cost_score = max(0.0, 100.0 - cost_pct * 100.0 - max(0.0, -cost_drag) * 0.01)
        source_score = min(100.0, useful_sources / max(2, total_sources) * 100.0)
        regime_score = max(0.0, 100.0 - regime_pct * 100.0)
        overfit_penalty = overfit_pct * 35.0
        coverage_penalty = (1.0 - coverage_ratio) * 40.0

        raw = (
            improvement_score * 0.20
            + return_score * 0.15
            + drawdown_score * 0.15
            + fragility_score * 0.20
            + cost_score * 0.10
            + source_score * 0.10
            + regime_score * 0.10
            - overfit_penalty
            - coverage_penalty
        )
        robustness = round(float(max(0, min(100, raw))), 2)
        klass = _classification(robustness, positive, ret, frag, overfit_pct >= 0.5, coverage_penalty)
        row = {
            "hypothesis_id": hypothesis_id,
            "signal_source": "MULTI_SOURCE",
            "scenario_name": "ALL",
            "windows_count": int(pd.to_numeric(base.get("windows_count"), errors="coerce").fillna(0).max()) if not base.empty else 0,
            "useful_cells": int(pd.to_numeric(base.get("useful_cells"), errors="coerce").fillna(0).sum()) if not base.empty else 0,
            "useful_sources_count": useful_sources,
            "positive_improvement_pct": round(positive, 4),
            "mean_return_delta": round(ret, 6),
            "mean_drawdown_delta": round(drawdown, 6),
            "mean_fragility_delta": round(frag, 6),
            "mean_cost_drag_delta": round(cost_drag, 6),
            "improvement_consistency_score": round(improvement_score, 2),
            "return_delta_score": round(return_score, 2),
            "drawdown_reduction_score": round(drawdown_score, 2),
            "fragility_reduction_score": round(fragility_score, 2),
            "cost_robustness_score": round(cost_score, 2),
            "source_diversity_score": round(source_score, 2),
            "regime_stability_score": round(regime_score, 2),
            "overfitting_penalty": round(overfit_penalty, 2),
            "data_coverage_penalty": round(coverage_penalty, 2),
            "cost_sensitivity_flag": bool(cost_pct >= 0.35),
            "overfitting_flag": bool(overfit_pct >= 0.5),
            "regime_instability_flag": bool(regime_pct >= 0.35),
            "hypothesis_robustness_score": robustness,
            "hypothesis_class": klass,
            "metadata_json": json.dumps({"validation_rows": base.to_dict("records"), "all_rows_count": int(len(group))}, ensure_ascii=False, default=str),
        }
        row["governance_status"] = evaluate_ranked_hypothesis(row)["governance_status"]
        rows.append(row)
    return pd.DataFrame(rows, columns=RANKING_COLUMNS).sort_values("hypothesis_robustness_score", ascending=False).reset_index(drop=True)


def generate_hypothesis_ranking_report(ranked_df: pd.DataFrame) -> str:
    if ranked_df is None or ranked_df.empty:
        return "Nenhum ranking de hipóteses em estudo foi gerado. Evidência insuficiente."
    lines = ["Ranking multi-fonte de hipóteses em estudo:"]
    for idx, row in ranked_df.reset_index(drop=True).iterrows():
        lines.append(
            f"{idx + 1}. {row['hypothesis_id']} - score {row['hypothesis_robustness_score']:.2f}, "
            f"{row['hypothesis_class']}, governança {row['governance_status']}, "
            f"fontes úteis {int(row.get('useful_sources_count') or 0)}."
        )
    lines.append("Não recomendação: ranking é simulação, investigação e validação.")
    return "\n".join(lines)

