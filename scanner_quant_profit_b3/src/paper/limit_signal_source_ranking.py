"""Ranking das variações LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import pandas as pd

from src.paper.limit_signal_source_governance import evaluate_limit_signal_source_variant


RANKING_COLUMNS = [
    "variant_id",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "mean_cost_drag_delta",
    "mean_slippage_delta",
    "trades_count",
    "removed_pct",
    "cost_sensitivity_flag",
    "slippage_sensitivity_flag",
    "overfitting_flag",
    "low_sample_flag",
    "source_diversity_score",
    "regime_stability_score",
    "variant_robustness_score",
    "variant_class",
    "governance_status",
    "metadata_json",
]


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _class(score: float, coverage_bad: bool) -> str:
    if coverage_bad:
        return "VARIANT_INSUFFICIENT_DATA"
    if score >= 75:
        return "VARIANT_ROBUST"
    if score >= 65:
        return "VARIANT_PROMISING"
    if score >= 55:
        return "VARIANT_OBSERVATION_ONLY"
    if score >= 40:
        return "VARIANT_FRAGILE"
    return "VARIANT_REJECTED"


def rank_limit_signal_source_variants(oos_df: pd.DataFrame) -> pd.DataFrame:
    if oos_df is None or oos_df.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)
    df = oos_df.copy()
    for col in ["positive_improvement_pct", "mean_return_delta", "mean_drawdown_delta", "mean_fragility_delta", "mean_cost_drag_delta", "mean_slippage_delta", "trades_count", "removed_pct"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)
    if "coverage_status" not in df.columns:
        df["coverage_status"] = "COVERAGE_USEFUL"
    for flag in ["cost_sensitivity_flag", "slippage_sensitivity_flag", "overfitting_flag", "low_sample_flag"]:
        if flag not in df.columns:
            df[flag] = False
    rows = []
    for variant_id, group in df.groupby("variant_id"):
        useful = group[group["coverage_status"].astype(str).eq("COVERAGE_USEFUL")]
        metric = useful if not useful.empty else group
        positive = float(metric["positive_improvement_pct"].mean())
        ret = float(metric["mean_return_delta"].mean())
        dd = float(metric["mean_drawdown_delta"].mean())
        frag = float(metric["mean_fragility_delta"].mean())
        cost = float(metric["mean_cost_drag_delta"].mean())
        slip = float(metric["mean_slippage_delta"].mean())
        removed = float(metric["removed_pct"].mean())
        trades = int(metric["trades_count"].sum())
        source_div = float(metric.loc[metric["trades_count"] > 0, "signal_source"].nunique() / max(1, df["signal_source"].nunique()))
        regime_stability = float((metric.groupby("regime")["positive_improvement_pct"].mean() >= 0.45).mean()) if "regime" in metric.columns else 0.0
        overfit = bool(metric.get("overfitting_flag", pd.Series(dtype=bool)).astype(bool).any())
        low_sample = bool(metric.get("low_sample_flag", pd.Series(dtype=bool)).astype(bool).any()) or trades < 20
        cost_flag = bool(metric.get("cost_sensitivity_flag", pd.Series(dtype=bool)).astype(bool).any())
        slip_flag = bool(metric.get("slippage_sensitivity_flag", pd.Series(dtype=bool)).astype(bool).any())
        score = 0.0
        score += positive * 25
        score += _clip((ret + 0.003) / 0.006 * 15, 0, 15)
        score += _clip((dd + 0.003) / 0.006 * 10, 0, 10)
        score += _clip((-frag + 5) / 10 * 20, 0, 20)
        score += 10 if cost <= 0 else 0
        score += 10 if slip <= 0 else 0
        score += _clip((1 - removed) * 10, 0, 10)
        score += source_div * 5
        score += regime_stability * 5
        if overfit:
            score -= 20
        if low_sample:
            score -= 15
        score = round(_clip(score), 2)
        row = {
            "variant_id": variant_id,
            "positive_improvement_pct": round(positive, 4),
            "mean_return_delta": round(ret, 6),
            "mean_drawdown_delta": round(dd, 6),
            "mean_fragility_delta": round(frag, 6),
            "mean_cost_drag_delta": round(cost, 6),
            "mean_slippage_delta": round(slip, 6),
            "trades_count": trades,
            "removed_pct": round(removed, 4),
            "cost_sensitivity_flag": cost_flag,
            "slippage_sensitivity_flag": slip_flag,
            "overfitting_flag": overfit,
            "low_sample_flag": low_sample,
            "source_diversity_score": round(source_div * 100, 2),
            "regime_stability_score": round(regime_stability * 100, 2),
            "variant_robustness_score": score,
            "metadata_json": "{}",
        }
        row["variant_class"] = _class(score, low_sample or metric["coverage_status"].astype(str).eq("EVIDENCIA_INSUFICIENTE").all())
        row["governance_status"] = evaluate_limit_signal_source_variant(pd.Series(row))
        rows.append(row)
    return pd.DataFrame(rows, columns=RANKING_COLUMNS).sort_values("variant_robustness_score", ascending=False).reset_index(drop=True)


def generate_limit_signal_source_ranking_report(ranked_df: pd.DataFrame) -> str:
    if ranked_df is None or ranked_df.empty:
        return "Evidência insuficiente para ranking de variações LIMIT_SIGNAL_SOURCE."
    lines = ["Ranking de variações LIMIT_SIGNAL_SOURCE", ""]
    for _, row in ranked_df.iterrows():
        lines.append(f"- {row['variant_id']}: score {row['variant_robustness_score']:.2f}, {row['variant_class']}, {row['governance_status']}")
    lines.append("")
    lines.append("Não recomendação: resultado de simulação, investigação e validação.")
    return "\n".join(lines)
