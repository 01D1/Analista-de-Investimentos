"""Validacao OOS e multi-cenario de hipoteses de investigacao."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd

from src.paper.fragility_by_asset import analyze_pnl_by_asset
from src.paper.fragility_score import calculate_fragility_score
from src.paper.hypothesis_validation_model import build_hypothesis_validation_scenarios
from src.paper.investigation_simulator import apply_investigation_hypothesis_to_signals
from src.paper.simulator import run_paper_simulation


RESULT_COLUMNS = [
    "window_id",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "base_return",
    "hypothesis_return",
    "return_delta",
    "base_drawdown",
    "hypothesis_drawdown",
    "drawdown_delta",
    "base_fragility_score",
    "hypothesis_fragility_score",
    "fragility_delta",
    "trades_count",
    "test_positive",
    "improvement_detected",
    "overfitting_flag",
    "cost_sensitivity_flag",
    "regime_instability_flag",
    "metadata_json",
]


def _hypothesis_dict(hypothesis: Any) -> dict:
    if isinstance(hypothesis, pd.Series):
        return hypothesis.to_dict()
    if is_dataclass(hypothesis):
        return asdict(hypothesis)
    return dict(hypothesis)


def create_hypothesis_oos_windows(start_date, end_date, train_months: int = 2, test_months: int = 1) -> pd.DataFrame:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    rows = []
    cursor = start
    idx = 1
    while cursor <= end:
        train_start = cursor
        train_end = train_start + pd.DateOffset(months=train_months) - pd.Timedelta(days=1)
        test_start = train_end + pd.Timedelta(days=1)
        test_end = test_start + pd.DateOffset(months=test_months) - pd.Timedelta(days=1)
        if test_start > end:
            break
        if test_end > end:
            test_end = end
        rows.append(
            {
                "window_id": idx,
                "train_start": train_start.date().isoformat(),
                "train_end": train_end.date().isoformat(),
                "test_start": test_start.date().isoformat(),
                "test_end": test_end.date().isoformat(),
            }
        )
        idx += 1
        cursor = cursor + pd.DateOffset(months=test_months)
    return pd.DataFrame(rows, columns=["window_id", "train_start", "train_end", "test_start", "test_end"])


def _slice(df: pd.DataFrame | None, start: str, end: str) -> pd.DataFrame:
    if df is None or df.empty or "trade_date" not in df.columns:
        return df.copy() if df is not None else pd.DataFrame()
    out = df.copy()
    out["trade_date"] = out["trade_date"].astype(str)
    return out[(out["trade_date"] >= str(start)) & (out["trade_date"] <= str(end))].copy()


def _signals_for_source(signals_df: pd.DataFrame, source: str) -> pd.DataFrame:
    if signals_df is None or signals_df.empty:
        return pd.DataFrame()
    if "signal_source" not in signals_df.columns or str(source).lower() in {"all", "*"}:
        return signals_df.copy()
    return signals_df[signals_df["signal_source"].astype(str).str.lower() == str(source).lower()].copy()


def _filter_by_regime(df: pd.DataFrame, regimes_df: pd.DataFrame | None, regime_filter: str) -> pd.DataFrame:
    if df is None or df.empty or not regime_filter or regimes_df is None or regimes_df.empty or "trade_date" not in df.columns:
        return df.copy() if df is not None else pd.DataFrame()
    regimes = regimes_df.copy()
    if "trade_date" not in regimes.columns:
        return df.copy()
    regime_cols = [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in regimes.columns]
    if not regime_cols:
        return df.copy()
    mask = pd.Series(False, index=regimes.index)
    for col in regime_cols:
        mask = mask | regimes[col].astype(str).str.upper().eq(str(regime_filter).upper())
    allowed_dates = set(regimes.loc[mask, "trade_date"].astype(str))
    return df[df["trade_date"].astype(str).isin(allowed_dates)].copy()


def _params(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _fragility_score(orders_df: pd.DataFrame, positions_df: pd.DataFrame, equity_df: pd.DataFrame) -> float:
    asset_df = analyze_pnl_by_asset(orders_df, positions_df, equity_df)
    if asset_df.empty:
        return 100.0
    total_trades = int(pd.to_numeric(asset_df.get("trades_count"), errors="coerce").fillna(0).sum())
    total_net_pnl = float(pd.to_numeric(asset_df.get("net_pnl"), errors="coerce").fillna(0).sum())
    cost_drag = float(pd.to_numeric(asset_df.get("total_cost_drag", asset_df.get("cost_drag")), errors="coerce").fillna(0).sum())
    max_drawdown = float(pd.to_numeric(equity_df.get("drawdown"), errors="coerce").fillna(0).min()) if equity_df is not None and not equity_df.empty else 0.0
    top_concentration = float(pd.to_numeric(asset_df.get("contribution_pct"), errors="coerce").abs().fillna(0).max())
    return float(
        calculate_fragility_score(
            {
                "trades_count": total_trades,
                "net_pnl": total_net_pnl,
                "cost_drag": cost_drag,
                "drawdown_contribution": abs(max_drawdown),
                "concentration_pct": top_concentration,
                "win_rate": 0.5,
            }
        )["fragility_score"]
    )


def _run_one(signals, prices, risk, start, end, scenario, hypothesis=None) -> dict:
    params = _params(scenario.get("parameters_json"))
    if hypothesis is not None:
        hyp = _hypothesis_dict(hypothesis)
        hyp_type = str(hyp.get("hypothesis_type", "")).upper()
        if hyp_type == "REDUCE_VOLATILITY_EXPOSURE":
            params["risk_pct"] = max(float(params.get("risk_pct", 0.005) or 0.005) * 0.5, 0.0005)
            params["max_positions"] = max(1, int(params.get("max_positions", 5) or 5) - 1)
        if hyp_type in {"DISABLE_REBALANCING", "REDUCE_REBALANCING"}:
            params["enable_rebalancing"] = False
    sim_signals = apply_investigation_hypothesis_to_signals(signals, hypothesis) if hypothesis is not None else signals
    result = run_paper_simulation(
        sim_signals,
        prices,
        risk_df=risk,
        start_date=start,
        end_date=end,
        capital=float(params.get("capital", 100000) or 100000),
        max_positions=int(params.get("max_positions", 5) or 5),
        risk_pct=float(params.get("risk_pct", 0.005) or 0.005),
        cost_bps=float(scenario.get("cost_bps", 10) or 10),
        slippage_bps=float(scenario.get("slippage_bps", 5) or 5),
        stop_loss_pct=float(params.get("stop_loss_pct", 0.03) or 0.03),
        take_profit_pct=float(params.get("take_profit_pct", 0.10) or 0.10),
        trailing_stop_pct=float(params.get("trailing_stop_pct", 0.04) or 0.04),
        daily_loss_limit_pct=float(params.get("daily_loss_limit_pct", 0.02) or 0.02),
        enable_rebalancing=bool(params.get("enable_rebalancing", False)),
    )
    summary = result.get("performance_summary", {})
    return {
        "return": float(summary.get("total_return", 0) or 0),
        "drawdown": float(summary.get("max_drawdown", 0) or 0),
        "trades": int(summary.get("trades_count", 0) or 0),
        "fragility": _fragility_score(result.get("orders_df", pd.DataFrame()), result.get("positions_df", pd.DataFrame()), result.get("equity_curve_df", pd.DataFrame())),
    }


def run_hypothesis_oos_validation(
    hypothesis,
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    regimes_df: pd.DataFrame | None = None,
    train_months: int = 2,
    test_months: int = 1,
    scenarios: pd.DataFrame | None = None,
) -> pd.DataFrame:
    hyp = _hypothesis_dict(hypothesis)
    if signals_df is None or signals_df.empty or prices_df is None or prices_df.empty or "trade_date" not in prices_df.columns:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    start = str(prices_df["trade_date"].astype(str).min())
    end = str(prices_df["trade_date"].astype(str).max())
    windows = create_hypothesis_oos_windows(start, end, train_months=train_months, test_months=test_months)
    if scenarios is None or scenarios.empty:
        scenarios = build_hypothesis_validation_scenarios(pd.DataFrame([hyp]), start, end)
    rows = []
    for _, window in windows.iterrows():
        test_start = str(window["test_start"])
        test_end = str(window["test_end"])
        for _, scenario in scenarios.iterrows():
            scenario_signals = _signals_for_source(signals_df, str(scenario.get("signal_source", "quant")))
            scenario_signals = _slice(scenario_signals, test_start, test_end)
            scenario_prices = _slice(prices_df, test_start, test_end)
            scenario_risk = _slice(risk_df, test_start, test_end) if risk_df is not None and not risk_df.empty and "trade_date" in risk_df.columns else risk_df
            regime_filter = str(scenario.get("regime_filter", "") or "")
            scenario_signals = _filter_by_regime(scenario_signals, regimes_df, regime_filter)
            scenario_prices = _filter_by_regime(scenario_prices, regimes_df, regime_filter)
            if scenario_prices.empty:
                base = {"return": 0.0, "drawdown": 0.0, "trades": 0, "fragility": 100.0}
                hyp_result = base.copy()
            else:
                base = _run_one(scenario_signals, scenario_prices, scenario_risk, test_start, test_end, scenario)
                hyp_result = _run_one(scenario_signals, scenario_prices, scenario_risk, test_start, test_end, scenario, hypothesis=hyp)
            return_delta = hyp_result["return"] - base["return"]
            drawdown_delta = hyp_result["drawdown"] - base["drawdown"]
            fragility_delta = hyp_result["fragility"] - base["fragility"]
            improvement = return_delta > 0 and (drawdown_delta >= 0 or fragility_delta < 0)
            overfit = hyp_result["trades"] < 20 or hyp_result["trades"] < base["trades"] * 0.5 if base["trades"] else hyp_result["trades"] < 5
            cost_flag = str(scenario.get("scenario_name", "")).upper() in {"HIGH_COST", "HIGH_SLIPPAGE"} and return_delta <= 0
            regime_flag = bool(regime_filter) and return_delta <= 0
            rows.append(
                {
                    "window_id": int(window["window_id"]),
                    "scenario_name": scenario.get("scenario_name"),
                    "signal_source": scenario.get("signal_source"),
                    "start_date": test_start,
                    "end_date": test_end,
                    "base_return": base["return"],
                    "hypothesis_return": hyp_result["return"],
                    "return_delta": return_delta,
                    "base_drawdown": base["drawdown"],
                    "hypothesis_drawdown": hyp_result["drawdown"],
                    "drawdown_delta": drawdown_delta,
                    "base_fragility_score": base["fragility"],
                    "hypothesis_fragility_score": hyp_result["fragility"],
                    "fragility_delta": fragility_delta,
                    "trades_count": hyp_result["trades"],
                    "test_positive": hyp_result["return"] > 0,
                    "improvement_detected": bool(improvement),
                    "overfitting_flag": bool(overfit),
                    "cost_sensitivity_flag": bool(cost_flag),
                    "regime_instability_flag": bool(regime_flag),
                    "metadata_json": json.dumps({"scenario": scenario.to_dict(), "window": window.to_dict(), "hypothesis": hyp}, ensure_ascii=False, default=str),
                }
            )
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def summarize_hypothesis_oos_validation(results_df: pd.DataFrame) -> dict:
    if results_df is None or results_df.empty:
        return {
            "windows_count": 0,
            "scenarios_count": 0,
            "positive_improvement_pct": 0.0,
            "mean_return_delta": 0.0,
            "mean_drawdown_delta": 0.0,
            "mean_fragility_delta": 0.0,
            "cost_sensitive_pct": 0.0,
            "regime_instability_pct": 0.0,
            "overfitting_pct": 0.0,
            "robustness_class": "HYPOTHESIS_INSUFFICIENT_DATA",
        }
    df = results_df.copy()
    improvements = df["improvement_detected"].astype(bool)
    trades = pd.to_numeric(df["trades_count"], errors="coerce").fillna(0)
    positive_pct = float(improvements.mean())
    mean_return_delta = float(pd.to_numeric(df["return_delta"], errors="coerce").fillna(0).mean())
    mean_drawdown_delta = float(pd.to_numeric(df["drawdown_delta"], errors="coerce").fillna(0).mean())
    mean_fragility_delta = float(pd.to_numeric(df["fragility_delta"], errors="coerce").fillna(0).mean())
    cost_pct = float(df["cost_sensitivity_flag"].astype(bool).mean())
    regime_pct = float(df["regime_instability_flag"].astype(bool).mean())
    overfit_pct = float(df["overfitting_flag"].astype(bool).mean())
    if len(df) < 3 or trades.mean() < 5:
        klass = "HYPOTHESIS_INSUFFICIENT_DATA"
    elif overfit_pct >= 0.5:
        klass = "HYPOTHESIS_OVERFIT_PROBABLE"
    elif positive_pct >= 0.60 and mean_return_delta > 0 and mean_fragility_delta < 0 and cost_pct < 0.35 and regime_pct < 0.35:
        klass = "HYPOTHESIS_ROBUST_FOR_OBSERVATION"
    elif positive_pct >= 0.45 and mean_return_delta > 0 and mean_fragility_delta <= 0:
        klass = "HYPOTHESIS_PROMISING"
    else:
        klass = "HYPOTHESIS_FRAGILE"
    return {
        "windows_count": int(df["window_id"].nunique()),
        "scenarios_count": int(df["scenario_name"].nunique()),
        "positive_improvement_pct": round(positive_pct, 4),
        "mean_return_delta": round(mean_return_delta, 6),
        "mean_drawdown_delta": round(mean_drawdown_delta, 6),
        "mean_fragility_delta": round(mean_fragility_delta, 6),
        "cost_sensitive_pct": round(cost_pct, 4),
        "regime_instability_pct": round(regime_pct, 4),
        "overfitting_pct": round(overfit_pct, 4),
        "robustness_class": klass,
    }
