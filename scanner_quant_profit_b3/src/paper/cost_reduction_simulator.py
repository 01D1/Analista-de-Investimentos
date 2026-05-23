"""Simulacao de variantes para reducao de custo no paper trading."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.cost_reduction_comparison import compare_cost_variant_to_baseline
from src.paper.cost_reduction_governance import evaluate_cost_reduction_variant
from src.paper.exit_rule_variants import apply_exit_rule_variant, build_exit_rule_variants
from src.paper.position_cost_lifecycle import link_orders_to_position_lifecycle, summarize_lifecycle_costs
from src.paper.rebalance_variants import apply_rebalance_variant, build_rebalance_variants
from src.paper.simulator import run_paper_simulation
from src.paper.turnover_diagnostics import analyze_turnover


SIMULATION_KEYS = {
    "start_date",
    "end_date",
    "capital",
    "max_positions",
    "risk_pct",
    "allow_rebalance",
    "cost_bps",
    "slippage_bps",
    "enable_rebalancing",
    "rebalance_frequency",
    "use_regime_adjustment",
    "stop_loss_pct",
    "take_profit_pct",
    "trailing_stop_pct",
    "atr_stop_multiplier",
    "fixed_holding_days",
    "daily_loss_limit_pct",
    "weekly_loss_limit_pct",
    "max_drawdown_pct",
    "min_holding_days_before_stop",
    "rebalance_min_delta_weight",
    "max_rebalance_turnover_pct",
    "close_positions_at_end",
}


def _simulation_kwargs(config: dict) -> dict:
    kwargs = {k: v for k, v in dict(config or {}).items() if k in SIMULATION_KEYS}
    if "start" in config and "start_date" not in kwargs:
        kwargs["start_date"] = config.get("start")
    if "end" in config and "end_date" not in kwargs:
        kwargs["end_date"] = config.get("end")
    return kwargs


def _metrics_from_result(result: dict, variant_id: str = "BASELINE", variant_type: str = "baseline") -> dict:
    orders = result.get("orders_df", pd.DataFrame())
    equity = result.get("equity_curve_df", pd.DataFrame())
    summary = dict(result.get("performance_summary", {}))
    lifecycle = link_orders_to_position_lifecycle(orders)
    lifecycle_summary = summarize_lifecycle_costs(lifecycle)
    turnover = analyze_turnover(orders, equity).get("summary", {})
    entry_cost = float(pd.to_numeric(lifecycle.get("entry_cost", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not lifecycle.empty else 0.0
    exit_cost = float(pd.to_numeric(lifecycle.get("exit_cost", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not lifecycle.empty else 0.0
    rebalance_cost = float(pd.to_numeric(lifecycle.get("rebalance_cost", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not lifecycle.empty else 0.0
    cost_drag = entry_cost + exit_cost + rebalance_cost
    return {
        "variant_id": variant_id,
        "variant_type": variant_type,
        "total_return": float(summary.get("total_return", 0) or 0),
        "max_drawdown": float(summary.get("max_drawdown", 0) or 0),
        "trades_count": int(summary.get("trades_count", 0) or 0),
        "cost_drag_total": round(cost_drag, 6),
        "entry_cost": round(entry_cost, 6),
        "exit_cost": round(exit_cost, 6),
        "rebalance_cost": round(rebalance_cost, 6),
        "profit_factor": float(summary.get("profit_factor", 0) or 0),
        "turnover": float(turnover.get("turnover_total", summary.get("turnover", 0)) or 0),
        "metadata_json": json.dumps({"lifecycle_summary": lifecycle_summary, "nao_recomendacao": True}, ensure_ascii=False, default=str),
    }


def run_cost_reduction_variants(
    base_config: dict,
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    rebalance_variants: pd.DataFrame | None = None,
    exit_rule_variants: pd.DataFrame | None = None,
    baseline_metrics: dict | None = None,
) -> pd.DataFrame:
    """Rodar baseline e variantes simuladas, comparando custo e performance."""
    if signals_df is None or signals_df.empty or prices_df is None or prices_df.empty:
        return pd.DataFrame(
            columns=[
                "variant_id",
                "variant_type",
                "total_return",
                "max_drawdown",
                "trades_count",
                "cost_drag_total",
                "entry_cost",
                "exit_cost",
                "rebalance_cost",
                "cost_reduction",
                "cost_reduction_pct",
                "return_delta",
                "drawdown_delta",
                "profit_factor",
                "turnover",
                "governance_status",
                "metadata_json",
            ]
        )
    base = dict(base_config or {})
    base.setdefault("exit_mode", "advanced")
    if baseline_metrics is None:
        baseline_result = run_paper_simulation(signals_df, prices_df, risk_df=risk_df, **_simulation_kwargs(base))
        baseline_metrics = _metrics_from_result(baseline_result)
    else:
        baseline_metrics = dict(baseline_metrics)
    variant_rows = []
    variants = []
    if rebalance_variants is not None:
        variants.extend(rebalance_variants.to_dict("records"))
    if exit_rule_variants is not None:
        variants.extend(exit_rule_variants.to_dict("records"))
    if not variants:
        variants = build_rebalance_variants().to_dict("records") + build_exit_rule_variants().to_dict("records")
    for variant in variants:
        vtype = str(variant.get("variant_type", "")).lower()
        config = apply_rebalance_variant(base, variant) if vtype == "rebalance" else apply_exit_rule_variant(base, variant)
        result = run_paper_simulation(signals_df, prices_df, risk_df=risk_df, **_simulation_kwargs(config))
        metrics = _metrics_from_result(result, variant.get("variant_id", "UNKNOWN"), vtype or "unknown")
        comparison = compare_cost_variant_to_baseline(baseline_metrics, metrics)
        metrics.update(comparison)
        metrics["baseline_trades_count"] = baseline_metrics.get("trades_count", 0)
        metrics["cost_reduction"] = round(-float(comparison.get("cost_drag_delta", 0) or 0), 6)
        base_cost = max(float(baseline_metrics.get("cost_drag_total", 0) or 0), 1.0)
        metrics["cost_reduction_pct"] = round(metrics["cost_reduction"] / base_cost, 6)
        metrics["governance_status"] = evaluate_cost_reduction_variant(metrics)
        metadata = json.loads(metrics.get("metadata_json") or "{}")
        metadata.update(
            {
                "variant_title": variant.get("title"),
                "parameters_json": variant.get("parameters_json"),
                "expected_effect": variant.get("expected_effect"),
                "comparison_class": comparison.get("comparison_class"),
                "baseline": baseline_metrics,
                "variant_simulada": True,
                "nao_recomendacao": True,
            }
        )
        metrics["metadata_json"] = json.dumps(metadata, ensure_ascii=False, default=str)
        variant_rows.append(metrics)
    return pd.DataFrame(variant_rows).sort_values(["improvement_score", "cost_reduction"], ascending=False).reset_index(drop=True)
