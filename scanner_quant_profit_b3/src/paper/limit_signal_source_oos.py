"""Validação OOS das variações LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.hypothesis_deep_oos import _fast_run_once, _regime_values
from src.paper.hypothesis_multi_source_validation import _filter_by_regime, _slice
from src.paper.hypothesis_oos_validation import create_hypothesis_oos_windows
from src.paper.limit_signal_source_apply import apply_limit_signal_source_variant


OOS_COLUMNS = [
    "variant_id",
    "signal_source",
    "cost_scenario",
    "slippage_scenario",
    "regime",
    "windows_count",
    "trades_count",
    "remaining_signals",
    "removed_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "mean_cost_drag_delta",
    "mean_slippage_delta",
    "positive_improvement_pct",
    "cost_sensitivity_flag",
    "slippage_sensitivity_flag",
    "overfitting_flag",
    "low_sample_flag",
    "coverage_status",
    "metadata_json",
]

DEFAULT_COSTS = {"LOW_COST": 5, "BASE_COST": 10, "HIGH_COST": 20, "STRESS_COST": 40}
DEFAULT_SLIPPAGE = {"LOW_SLIPPAGE": 2, "BASE_SLIPPAGE": 5, "HIGH_SLIPPAGE": 20}


def _scenario_costs(enabled: dict[str, float] | None, default: dict[str, float]) -> dict[str, float]:
    return enabled or default


def _drag(bps: float, trades: int) -> float:
    return float(bps or 0) / 10000 * int(trades or 0) * 1000


def _context_for_window(signals_by_source: dict[str, pd.DataFrame], regimes_df: pd.DataFrame | None, scenario_cost_bps: float, scenario_slippage_bps: float, source: str, window_regimes: pd.DataFrame | None) -> dict:
    source_counts = {k: len(v) for k, v in (signals_by_source or {}).items() if v is not None}
    total = max(1, sum(source_counts.values()))
    return {
        "signals_by_source": signals_by_source,
        "regimes_df": window_regimes if window_regimes is not None else regimes_df,
        "signal_source": source,
        "source_cost_drag": {k: scenario_cost_bps / 10000 * (count / total) for k, count in source_counts.items()},
        "source_slippage": {k: scenario_slippage_bps / 10000 * (count / total) for k, count in source_counts.items()},
        "source_turnover": {k: count / total for k, count in source_counts.items()},
    }


def run_limit_signal_source_oos(
    variants_df: pd.DataFrame,
    signals_by_source: dict[str, pd.DataFrame],
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    regimes_df: pd.DataFrame | None = None,
    cost_scenarios: dict[str, float] | None = None,
    slippage_scenarios: dict[str, float] | None = None,
    train_months: int = 1,
    test_months: int = 1,
) -> pd.DataFrame:
    if variants_df is None or variants_df.empty or prices_df is None or prices_df.empty:
        return pd.DataFrame(columns=OOS_COLUMNS)
    start = str(prices_df["trade_date"].astype(str).min())
    end = str(prices_df["trade_date"].astype(str).max())
    windows = create_hypothesis_oos_windows(start, end, train_months=train_months, test_months=test_months)
    if windows.empty:
        return pd.DataFrame(columns=OOS_COLUMNS)
    costs = _scenario_costs(cost_scenarios, DEFAULT_COSTS)
    slippages = _scenario_costs(slippage_scenarios, DEFAULT_SLIPPAGE)
    regimes = _regime_values(regimes_df)
    rows = []
    active_sources = {k: v.copy() for k, v in (signals_by_source or {}).items() if v is not None and not v.empty}

    for _, variant in variants_df.iterrows():
        for source, source_signals_all in active_sources.items():
            source_signals_all = source_signals_all.copy()
            source_signals_all["signal_source"] = source
            for cost_name, cost_bps in costs.items():
                for slip_name, slip_bps in slippages.items():
                    for regime in regimes:
                        metrics = []
                        summaries = []
                        for _, window in windows.iterrows():
                            test_start = str(window["test_start"])
                            test_end = str(window["test_end"])
                            window_sources = {k: _slice(v, test_start, test_end) for k, v in active_sources.items()}
                            sig = window_sources.get(source, pd.DataFrame())
                            px = _slice(prices_df, test_start, test_end)
                            window_regimes = _slice(regimes_df, test_start, test_end) if regimes_df is not None and not regimes_df.empty and "trade_date" in regimes_df.columns else regimes_df
                            if regime != "SEM_REGIME":
                                sig = _filter_by_regime(sig, regimes_df, regime)
                                px = _filter_by_regime(px, regimes_df, regime)
                                window_sources = {k: _filter_by_regime(v, regimes_df, regime) for k, v in window_sources.items()}
                            if sig.empty or px.empty:
                                continue
                            context = _context_for_window(window_sources, regimes_df, float(cost_bps), float(slip_bps), source, window_regimes)
                            filtered, removed, summary = apply_limit_signal_source_variant(sig, variant, context=context)
                            scenario = {"scenario_name": f"{cost_name}_{slip_name}_{regime}", "cost_bps": cost_bps, "slippage_bps": slip_bps}
                            base = _fast_run_once(sig, px, scenario)
                            after = _fast_run_once(filtered, px, scenario, hypothesis={"hypothesis_type": "LIMIT_SIGNAL_SOURCE"})
                            metrics.append(
                                {
                                    "return_delta": after["return"] - base["return"],
                                    "drawdown_delta": after["drawdown"] - base["drawdown"],
                                    "fragility_delta": after["fragility"] - base["fragility"],
                                    "cost_drag_delta": _drag(cost_bps, after["trades"]) - _drag(cost_bps, base["trades"]),
                                    "slippage_delta": _drag(slip_bps, after["trades"]) - _drag(slip_bps, base["trades"]),
                                    "trades": after["trades"],
                                    "base_trades": base["trades"],
                                    "remaining_signals": summary["remaining_signals"],
                                    "removed_pct": summary["removed_pct"],
                                }
                            )
                            summaries.append(summary)
                        metric_df = pd.DataFrame(metrics)
                        if metric_df.empty:
                            rows.append(
                                {
                                    "variant_id": variant.get("variant_id"),
                                    "signal_source": source,
                                    "cost_scenario": cost_name,
                                    "slippage_scenario": slip_name,
                                    "regime": regime,
                                    "windows_count": int(len(windows)),
                                    "trades_count": 0,
                                    "remaining_signals": 0,
                                    "removed_pct": 0.0,
                                    "mean_return_delta": 0.0,
                                    "mean_drawdown_delta": 0.0,
                                    "mean_fragility_delta": 0.0,
                                    "mean_cost_drag_delta": 0.0,
                                    "mean_slippage_delta": 0.0,
                                    "positive_improvement_pct": 0.0,
                                    "cost_sensitivity_flag": False,
                                    "slippage_sensitivity_flag": False,
                                    "overfitting_flag": True,
                                    "low_sample_flag": True,
                                    "coverage_status": "EVIDENCIA_INSUFICIENTE",
                                    "metadata_json": json.dumps({"variant": variant.to_dict(), "summaries": summaries}, ensure_ascii=False, default=str),
                                }
                            )
                            continue
                        positive = (metric_df["fragility_delta"] < 0) & (metric_df["return_delta"] >= -0.001) & (metric_df["cost_drag_delta"] <= 0) & (metric_df["slippage_delta"] <= 0)
                        low_sample = bool(metric_df["trades"].mean() < 5)
                        overfit = bool(((metric_df["base_trades"] > 0) & (metric_df["trades"] < metric_df["base_trades"] * 0.45)).mean() >= 0.5)
                        rows.append(
                            {
                                "variant_id": variant.get("variant_id"),
                                "signal_source": source,
                                "cost_scenario": cost_name,
                                "slippage_scenario": slip_name,
                                "regime": regime,
                                "windows_count": int(len(windows)),
                                "trades_count": int(metric_df["trades"].sum()),
                                "remaining_signals": int(metric_df["remaining_signals"].sum()),
                                "removed_pct": round(float(metric_df["removed_pct"].mean()), 4),
                                "mean_return_delta": round(float(metric_df["return_delta"].mean()), 6),
                                "mean_drawdown_delta": round(float(metric_df["drawdown_delta"].mean()), 6),
                                "mean_fragility_delta": round(float(metric_df["fragility_delta"].mean()), 6),
                                "mean_cost_drag_delta": round(float(metric_df["cost_drag_delta"].mean()), 6),
                                "mean_slippage_delta": round(float(metric_df["slippage_delta"].mean()), 6),
                                "positive_improvement_pct": round(float(positive.mean()), 4),
                                "cost_sensitivity_flag": bool(("HIGH" in cost_name or "STRESS" in cost_name) and metric_df["return_delta"].mean() < 0),
                                "slippage_sensitivity_flag": bool("HIGH" in slip_name and metric_df["return_delta"].mean() < 0),
                                "overfitting_flag": overfit,
                                "low_sample_flag": low_sample,
                                "coverage_status": "COVERAGE_USEFUL" if len(metric_df) >= max(1, len(windows) // 2) else "EVIDENCIA_INSUFICIENTE",
                                "metadata_json": json.dumps({"variant": variant.to_dict(), "summaries": summaries}, ensure_ascii=False, default=str),
                            }
                        )
    return pd.DataFrame(rows, columns=OOS_COLUMNS)
