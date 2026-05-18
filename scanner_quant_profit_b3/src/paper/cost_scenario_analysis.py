"""Analise de sensibilidade a custo e slippage no paper trading."""
from __future__ import annotations

import pandas as pd


def build_cost_scenarios() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"scenario_id": "COST_LOW", "scenario_name": "COST_LOW", "cost_bps": 5, "slippage_bps": 2},
            {"scenario_id": "COST_BASE", "scenario_name": "COST_BASE", "cost_bps": 10, "slippage_bps": 5},
            {"scenario_id": "COST_HIGH", "scenario_name": "COST_HIGH", "cost_bps": 20, "slippage_bps": 10},
            {"scenario_id": "COST_STRESS", "scenario_name": "COST_STRESS", "cost_bps": 30, "slippage_bps": 20},
        ]
    )


def analyze_cost_sensitivity(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["cost_scenario", "cost_bps", "slippage_bps", "mean_return", "mean_drawdown", "positive_periods_pct", "profit_factor", "return_sensitivity", "cost_robustness_class", "metadata_json"]
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=columns)
    df = results_df.copy()
    df["cost_scenario"] = df.get("scenario_name", "").astype(str)
    rows = []
    grouped = df.groupby(["cost_scenario", "cost_bps", "slippage_bps"], dropna=False)
    base_return = None
    for (scenario, cost, slip), group in grouped:
        ret = pd.to_numeric(group["total_return"], errors="coerce").fillna(0)
        dd = pd.to_numeric(group["max_drawdown"], errors="coerce").fillna(0)
        pf = pd.to_numeric(group["profit_factor"], errors="coerce").fillna(0)
        mean_ret = float(ret.mean())
        if base_return is None or float(cost) <= 10:
            base_return = mean_ret if base_return is None else base_return
        sensitivity = mean_ret - (base_return or 0)
        if len(group) < 2:
            klass = "COST_INSUFFICIENT_DATA"
        elif mean_ret > 0 and sensitivity > -0.01:
            klass = "COST_ROBUST"
        elif mean_ret > 0:
            klass = "COST_SENSITIVE"
        else:
            klass = "COST_FRAGILE"
        rows.append(
            {
                "cost_scenario": scenario,
                "cost_bps": float(cost),
                "slippage_bps": float(slip),
                "mean_return": round(mean_ret, 6),
                "mean_drawdown": round(float(dd.mean()), 6),
                "positive_periods_pct": round(float((ret > 0).mean()), 4),
                "profit_factor": round(float(pf.mean()), 6),
                "return_sensitivity": round(float(sensitivity), 6),
                "cost_robustness_class": klass,
                "metadata_json": "{}",
            }
        )
    return pd.DataFrame(rows, columns=columns)
