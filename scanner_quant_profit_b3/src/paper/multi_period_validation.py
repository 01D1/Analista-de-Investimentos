"""Validacao multi-periodo e multi-cenario da carteira simulada."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.paper_governance import evaluate_paper_simulation
from src.paper.simulator import run_paper_simulation


RESULT_COLUMNS = [
    "period_id",
    "scenario_id",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "total_return",
    "max_drawdown",
    "sharpe",
    "sortino",
    "win_rate",
    "profit_factor",
    "trades_count",
    "turnover",
    "exposure_avg",
    "cost_bps",
    "slippage_bps",
    "governance_status",
    "metadata_json",
]


def create_validation_periods(start_date, end_date, window_months: int = 3, step_months: int = 1) -> pd.DataFrame:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    rows = []
    cursor = start
    idx = 1
    while cursor <= end:
        period_end = cursor + pd.DateOffset(months=window_months) - pd.Timedelta(days=1)
        if period_end > end:
            period_end = end
        if cursor > period_end:
            break
        rows.append({"period_id": idx, "start_date": cursor.date().isoformat(), "end_date": period_end.date().isoformat()})
        if period_end >= end:
            break
        cursor = cursor + pd.DateOffset(months=step_months)
        idx += 1
    return pd.DataFrame(rows, columns=["period_id", "start_date", "end_date"])


def _slice(df: pd.DataFrame | None, start: str, end: str) -> pd.DataFrame:
    if df is None or df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["trade_date"] = work["trade_date"].astype(str)
    return work[(work["trade_date"] >= str(start)) & (work["trade_date"] <= str(end))]


def _signals_for_source(signals_df: pd.DataFrame, source: str) -> pd.DataFrame:
    if signals_df is None or signals_df.empty:
        return pd.DataFrame()
    if "signal_source" not in signals_df.columns or source in {"all", "*"}:
        return signals_df.copy()
    return signals_df[signals_df["signal_source"].astype(str).str.lower() == str(source).lower()].copy()


def _scenario_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "sim"}


def run_multi_period_validation(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None,
    scenarios: pd.DataFrame,
    periods: pd.DataFrame,
    capital: float = 100_000,
) -> pd.DataFrame:
    if scenarios is None or scenarios.empty or periods is None or periods.empty or prices_df is None or prices_df.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    rows = []
    for _, period in periods.iterrows():
        start = str(period["start_date"])
        end = str(period["end_date"])
        period_prices = _slice(prices_df, start, end)
        period_risk = _slice(risk_df, start, end) if risk_df is not None and not risk_df.empty else risk_df
        for _, scenario in scenarios.iterrows():
            source = str(scenario.get("signal_source", "quant")).lower()
            period_signals = _slice(_signals_for_source(signals_df, source), start, end)
            result = run_paper_simulation(
                period_signals,
                period_prices,
                risk_df=period_risk,
                start_date=start,
                end_date=end,
                capital=capital,
                max_positions=int(scenario.get("max_positions", 5) or 5),
                risk_pct=float(scenario.get("risk_pct", 0.005) or 0.005),
                cost_bps=float(scenario.get("cost_bps", 10) or 0),
                slippage_bps=float(scenario.get("slippage_bps", 5) or 0),
                stop_loss_pct=scenario.get("stop_loss_pct") if pd.notna(scenario.get("stop_loss_pct")) else None,
                take_profit_pct=scenario.get("take_profit_pct") if pd.notna(scenario.get("take_profit_pct")) else None,
                trailing_stop_pct=scenario.get("trailing_stop_pct") if pd.notna(scenario.get("trailing_stop_pct")) else None,
                daily_loss_limit_pct=scenario.get("daily_loss_limit_pct") if pd.notna(scenario.get("daily_loss_limit_pct")) else None,
                enable_rebalancing=_scenario_bool(scenario.get("enable_rebalancing", False)),
                use_regime_adjustment=_scenario_bool(scenario.get("use_regime_adjustment", False)),
            )
            summary = result["performance_summary"].copy()
            governance = evaluate_paper_simulation(summary)
            rows.append(
                {
                    "period_id": int(period["period_id"]),
                    "scenario_id": scenario.get("scenario_id"),
                    "scenario_name": scenario.get("scenario_name"),
                    "signal_source": source,
                    "start_date": start,
                    "end_date": end,
                    "total_return": float(summary.get("total_return", 0) or 0),
                    "max_drawdown": float(summary.get("max_drawdown", 0) or 0),
                    "sharpe": float(summary.get("sharpe", 0) or 0),
                    "sortino": float(summary.get("sortino", 0) or 0),
                    "win_rate": float(summary.get("win_rate", 0) or 0),
                    "profit_factor": float(summary.get("profit_factor", 0) or 0),
                    "trades_count": int(summary.get("trades_count", summary.get("turnover", 0)) or 0),
                    "turnover": float(summary.get("turnover", 0) or 0),
                    "exposure_avg": float(summary.get("exposure_avg", 0) or 0),
                    "cost_bps": float(scenario.get("cost_bps", 10) or 0),
                    "slippage_bps": float(scenario.get("slippage_bps", 5) or 0),
                    "governance_status": governance["governance_status"],
                    "metadata_json": json.dumps({"scenario": scenario.to_dict(), "governance": governance}, ensure_ascii=False, default=str),
                }
            )
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def summarize_multi_period_validation(results_df: pd.DataFrame) -> dict:
    if results_df is None or results_df.empty:
        return {
            "scenarios_count": 0,
            "periods_count": 0,
            "signal_sources_count": 0,
            "mean_return": 0.0,
            "median_return": 0.0,
            "positive_periods_pct": 0.0,
            "worst_period_return": 0.0,
            "best_period_return": 0.0,
            "mean_drawdown": 0.0,
            "stability": 0.0,
            "robustness": "PAPER_SCENARIO_INSUFFICIENT_DATA",
        }
    df = results_df.copy()
    returns = pd.to_numeric(df["total_return"], errors="coerce").fillna(0)
    drawdown = pd.to_numeric(df["max_drawdown"], errors="coerce").fillna(0)
    positive_pct = float((returns > 0).mean())
    mean_return = float(returns.mean())
    stability = float(1 / (1 + returns.std())) if len(returns) > 1 else 0.0
    avg_trades = float(pd.to_numeric(df["trades_count"], errors="coerce").fillna(0).mean())
    if len(df) < 4 or avg_trades < 5:
        robustness = "PAPER_SCENARIO_INSUFFICIENT_DATA"
    elif positive_pct >= 0.60 and mean_return > 0 and abs(float(drawdown.mean())) <= 0.15:
        robustness = "PAPER_SCENARIO_ROBUST"
    elif positive_pct >= 0.50 and mean_return > 0:
        robustness = "PAPER_SCENARIO_PROMISING"
    else:
        robustness = "PAPER_SCENARIO_FRAGILE"
    return {
        "scenarios_count": int(df["scenario_id"].nunique()),
        "periods_count": int(df["period_id"].nunique()),
        "signal_sources_count": int(df["signal_source"].nunique()),
        "mean_return": round(mean_return, 6),
        "median_return": round(float(returns.median()), 6),
        "positive_periods_pct": round(positive_pct, 4),
        "worst_period_return": round(float(returns.min()), 6),
        "best_period_return": round(float(returns.max()), 6),
        "mean_drawdown": round(float(drawdown.mean()), 6),
        "stability": round(stability, 6),
        "robustness": robustness,
    }
