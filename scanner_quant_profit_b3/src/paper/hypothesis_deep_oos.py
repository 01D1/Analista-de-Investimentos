"""Validação OOS profunda de hipóteses em estudo."""
from __future__ import annotations

import pandas as pd

from src.paper.fragility_score import calculate_fragility_score
from src.paper.hypothesis_multi_source_validation import _apply_hypothesis, _filter_by_regime, _slice
from src.paper.hypothesis_oos_validation import create_hypothesis_oos_windows


DEEP_OOS_COLUMNS = [
    "hypothesis_id",
    "signal_source",
    "cost_scenario",
    "slippage_scenario",
    "regime",
    "ticker",
    "windows_count",
    "trades_count",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "positive_improvement_pct",
    "overfitting_flag",
    "cost_sensitivity_flag",
    "slippage_sensitivity_flag",
    "regime_instability_flag",
    "asset_concentration_flag",
    "data_coverage_status",
    "block_reason",
]


DEFAULT_COSTS = {"LOW_COST": 5, "BASE_COST": 10, "HIGH_COST": 20, "STRESS_COST": 40}
DEFAULT_SLIPPAGE = {"LOW_SLIPPAGE": 2, "BASE_SLIPPAGE": 5, "HIGH_SLIPPAGE": 20}
DEFAULT_REGIMES = ["SEM_REGIME", "LATERAL", "ALTA_TENDENCIAL", "BAIXA_TENDENCIAL", "ALTA_VOLATILIDADE", "LIQUIDEZ_FRACA"]


def _block_reason(metrics: pd.DataFrame, cost_name: str, slippage_name: str, regime: str) -> str:
    if metrics.empty:
        return "BLOCKED_BY_LOW_SAMPLE"
    if bool((metrics["trades"] < 5).mean() >= 0.5):
        return "BLOCKED_BY_LOW_SAMPLE"
    if bool((metrics["trades"] < metrics["base_trades"] * 0.5).mean() >= 0.5):
        return "BLOCKED_BY_OVERFITTING"
    if "HIGH" in cost_name or "STRESS" in cost_name:
        if float(metrics["return_delta"].mean()) < 0:
            return "BLOCKED_BY_COST"
    if "HIGH" in slippage_name and float(metrics["return_delta"].mean()) < 0:
        return "BLOCKED_BY_SLIPPAGE"
    if regime != "SEM_REGIME" and float(metrics["return_delta"].mean()) < 0:
        return "BLOCKED_BY_REGIME"
    if float(metrics["return_delta"].mean()) < 0:
        return "BLOCKED_BY_NEGATIVE_RETURN"
    if float(metrics["drawdown_delta"].mean()) < 0:
        return "BLOCKED_BY_DRAWDAWN"
    if float(metrics["fragility_delta"].mean()) >= 0:
        return "MIXED_EVIDENCE"
    return "NO_CLEAR_BLOCKER"


def _fast_run_once(signals: pd.DataFrame, prices: pd.DataFrame, scenario: dict, hypothesis: dict | None = None) -> dict:
    if signals is None or signals.empty or prices is None or prices.empty:
        return {"return": 0.0, "drawdown": 0.0, "trades": 0, "fragility": 100.0, "cost_drag": 0.0}
    sig = signals.copy()
    px = prices.copy()
    sig["trade_date"] = sig["trade_date"].astype(str)
    sig["ticker"] = sig["ticker"].astype(str).str.upper()
    px["trade_date"] = px["trade_date"].astype(str)
    px["ticker"] = px["ticker"].astype(str).str.upper()
    px["close"] = pd.to_numeric(px.get("close"), errors="coerce")
    daily = px[["trade_date", "ticker", "close"]].dropna().sort_values(["ticker", "trade_date"])
    if daily.empty:
        return {"return": 0.0, "drawdown": 0.0, "trades": int(len(sig)), "fragility": 100.0, "cost_drag": 0.0}
    last_by_ticker = daily.groupby("ticker", as_index=False).tail(1).rename(columns={"close": "exit_close"})[["ticker", "exit_close"]]
    entry = sig.merge(daily.rename(columns={"close": "entry_close"}), on=["trade_date", "ticker"], how="left").merge(last_by_ticker, on="ticker", how="left")
    if entry.empty:
        return {"return": 0.0, "drawdown": 0.0, "trades": 0, "fragility": 100.0, "cost_drag": 0.0}
    gross = (pd.to_numeric(entry["exit_close"], errors="coerce") / pd.to_numeric(entry["entry_close"], errors="coerce")) - 1
    score = pd.to_numeric(entry.get("signal_score"), errors="coerce").fillna(50)
    weight = (score / 100).clip(0.25, 1.0)
    hyp_type = str((hypothesis or {}).get("hypothesis_type", "")).upper()
    exposure_multiplier = 0.5 if hyp_type == "REDUCE_VOLATILITY_EXPOSURE" else 0.75 if hyp_type == "LIMIT_ASSET_WEIGHT" else 1.0
    cost_drag = (float(scenario.get("cost_bps", 10) or 10) + float(scenario.get("slippage_bps", 5) or 5)) / 10000
    net = (gross.fillna(0) * weight * exposure_multiplier) - cost_drag
    trades = int(len(entry))
    total_return = float(net.mean()) if trades else 0.0
    drawdown = float(min(0.0, net.min())) if trades else 0.0
    concentration = float(sig["ticker"].value_counts(normalize=True).max()) if trades else 0.0
    total_net_pnl = total_return * trades * 1000
    fragility = float(
        calculate_fragility_score(
            {
                "trades_count": trades,
                "net_pnl": total_net_pnl,
                "cost_drag": cost_drag * trades * 1000,
                "drawdown_contribution": abs(drawdown),
                "concentration_pct": concentration,
                "win_rate": float((net > 0).mean()) if trades else 0.0,
            }
        )["fragility_score"]
    )
    return {"return": total_return, "drawdown": drawdown, "trades": trades, "fragility": fragility, "cost_drag": cost_drag * trades * 1000}


def _regime_values(regimes_df: pd.DataFrame | None) -> list[str]:
    if regimes_df is None or regimes_df.empty:
        return ["SEM_REGIME"]
    cols = [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in regimes_df.columns]
    found: list[str] = []
    for col in cols:
        for value in regimes_df[col].dropna().astype(str).str.upper().unique().tolist():
            if value in DEFAULT_REGIMES and value not in found:
                found.append(value)
    return ["SEM_REGIME"] + found[:3]


def run_deep_oos_validation(
    hypothesis,
    signals_by_source: dict[str, pd.DataFrame],
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    regimes_df: pd.DataFrame | None = None,
    events_df: pd.DataFrame | None = None,
    cost_scenarios: dict[str, float] | None = None,
    slippage_scenarios: dict[str, float] | None = None,
    train_months: int = 1,
    test_months: int = 1,
    include_assets: bool = True,
    max_assets_per_source: int = 3,
) -> pd.DataFrame:
    hyp = dict(hypothesis)
    if prices_df is None or prices_df.empty:
        return pd.DataFrame(columns=DEEP_OOS_COLUMNS)
    start = str(prices_df["trade_date"].astype(str).min())
    end = str(prices_df["trade_date"].astype(str).max())
    windows = create_hypothesis_oos_windows(start, end, train_months=train_months, test_months=test_months)
    if windows.empty:
        return pd.DataFrame(columns=DEEP_OOS_COLUMNS)
    costs = cost_scenarios or DEFAULT_COSTS
    slippages = slippage_scenarios or DEFAULT_SLIPPAGE
    regimes = _regime_values(regimes_df)
    rows = []
    for source, source_signals in (signals_by_source or {}).items():
        if source_signals is None or source_signals.empty:
            continue
        tickers = ["TODOS"]
        if include_assets and "ticker" in source_signals.columns:
            top_tickers = source_signals["ticker"].dropna().astype(str).str.upper().value_counts().head(int(max_assets_per_source)).index.tolist()
            tickers += sorted(top_tickers)
        for cost_name, cost_bps in costs.items():
            for slip_name, slip_bps in slippages.items():
                for regime in regimes:
                    for ticker in tickers:
                        metrics = []
                        for _, window in windows.iterrows():
                            test_start = str(window["test_start"])
                            test_end = str(window["test_end"])
                            sig = _slice(source_signals, test_start, test_end)
                            if ticker != "TODOS" and not sig.empty:
                                sig = sig[sig["ticker"].astype(str).str.upper().eq(ticker)].copy()
                            px = _slice(prices_df, test_start, test_end)
                            if ticker != "TODOS" and not px.empty:
                                px = px[px["ticker"].astype(str).str.upper().eq(ticker)].copy()
                            if regime != "SEM_REGIME":
                                sig = _filter_by_regime(sig, regimes_df, regime)
                                px = _filter_by_regime(px, regimes_df, regime)
                            if sig.empty or px.empty:
                                continue
                            scenario = {
                                "scenario_name": f"{cost_name}_{slip_name}_{regime}",
                                "cost_bps": cost_bps,
                                "slippage_bps": slip_bps,
                                "parameters_json": '{"risk_pct": 0.005, "max_positions": 5}',
                            }
                            hyp_sig = _apply_hypothesis(sig, hyp, signals_by_source, regimes_df)
                            base = _fast_run_once(sig, px, scenario)
                            after = _fast_run_once(hyp_sig, px, scenario, hypothesis=hyp)
                            metrics.append(
                                {
                                    "return_delta": after["return"] - base["return"],
                                    "drawdown_delta": after["drawdown"] - base["drawdown"],
                                    "fragility_delta": after["fragility"] - base["fragility"],
                                    "trades": after["trades"],
                                    "base_trades": base["trades"],
                                }
                            )
                        metric_df = pd.DataFrame(metrics)
                        positive = ((metric_df.get("fragility_delta", pd.Series(dtype=float)) < 0) & (metric_df.get("return_delta", pd.Series(dtype=float)) >= -0.001)).mean() if not metric_df.empty else 0.0
                        reason = _block_reason(metric_df, cost_name, slip_name, regime)
                        rows.append(
                            {
                                "hypothesis_id": hyp.get("hypothesis_id"),
                                "signal_source": source,
                                "cost_scenario": cost_name,
                                "slippage_scenario": slip_name,
                                "regime": regime,
                                "ticker": ticker,
                                "windows_count": int(len(windows)),
                                "trades_count": int(metric_df["trades"].sum()) if not metric_df.empty else 0,
                                "mean_return_delta": round(float(metric_df["return_delta"].mean()), 6) if not metric_df.empty else 0.0,
                                "mean_drawdown_delta": round(float(metric_df["drawdown_delta"].mean()), 6) if not metric_df.empty else 0.0,
                                "mean_fragility_delta": round(float(metric_df["fragility_delta"].mean()), 6) if not metric_df.empty else 0.0,
                                "positive_improvement_pct": round(float(positive), 4),
                                "overfitting_flag": reason == "BLOCKED_BY_OVERFITTING",
                                "cost_sensitivity_flag": reason == "BLOCKED_BY_COST",
                                "slippage_sensitivity_flag": reason == "BLOCKED_BY_SLIPPAGE",
                                "regime_instability_flag": reason == "BLOCKED_BY_REGIME",
                                "asset_concentration_flag": ticker != "TODOS" and reason not in {"NO_CLEAR_BLOCKER", "BLOCKED_BY_LOW_SAMPLE"},
                                "data_coverage_status": "COVERAGE_USEFUL" if len(metric_df) >= max(1, len(windows) // 2) else "EVIDENCIA_INSUFICIENTE",
                                "block_reason": reason,
                            }
                        )
    return pd.DataFrame(rows, columns=DEEP_OOS_COLUMNS)
