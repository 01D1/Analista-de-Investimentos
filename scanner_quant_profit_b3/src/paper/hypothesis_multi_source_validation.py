"""Validação multi-fonte de hipóteses em estudo."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd

from src.paper.fragility_by_asset import analyze_pnl_by_asset
from src.paper.fragility_score import calculate_fragility_score
from src.paper.hypothesis_oos_validation import create_hypothesis_oos_windows
from src.paper.simulator import run_paper_simulation


VALIDATION_COLUMNS = [
    "hypothesis_id",
    "signal_source",
    "scenario_name",
    "windows_count",
    "useful_cells",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "mean_cost_drag_delta",
    "overfitting_flag",
    "cost_sensitivity_flag",
    "regime_instability_flag",
    "data_coverage_status",
    "governance_status",
    "metadata_json",
]


def _hypothesis_dict(hypothesis: Any) -> dict:
    if isinstance(hypothesis, pd.Series):
        return hypothesis.to_dict()
    if is_dataclass(hypothesis):
        return asdict(hypothesis)
    return dict(hypothesis)


def _params(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _slice(df: pd.DataFrame | None, start: str, end: str) -> pd.DataFrame:
    if df is None or df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    out["trade_date"] = out["trade_date"].astype(str)
    return out[(out["trade_date"] >= str(start)) & (out["trade_date"] <= str(end))].copy()


def _filter_by_regime(df: pd.DataFrame, regimes_df: pd.DataFrame | None, regime_filter: str) -> pd.DataFrame:
    if df.empty or not regime_filter or regimes_df is None or regimes_df.empty or "trade_date" not in df.columns:
        return df.copy()
    regimes = regimes_df.copy()
    regimes["trade_date"] = regimes["trade_date"].astype(str)
    cols = [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in regimes.columns]
    if not cols:
        return df.copy()
    mask = pd.Series(False, index=regimes.index)
    for col in cols:
        mask = mask | regimes[col].astype(str).str.upper().eq(str(regime_filter).upper())
    dates = set(regimes.loc[mask, "trade_date"])
    return df[df["trade_date"].astype(str).isin(dates)].copy()


def _metadata_filter_tickers(signals: pd.DataFrame, mode: str, params: dict) -> set[str]:
    if signals.empty or "ticker" not in signals.columns:
        return set()
    if mode == "low_sample":
        counts = signals["ticker"].astype(str).str.upper().value_counts()
        return set(counts[counts < int(params.get("min_ticker_signals", 3))].index)
    if mode == "worst_return" and "net_return_5d" in signals.columns:
        work = signals.copy()
        work["_ret"] = pd.to_numeric(work["net_return_5d"], errors="coerce")
        by_ticker = work.groupby("ticker")["_ret"].mean().dropna()
        if by_ticker.empty:
            return set()
        cutoff = by_ticker.quantile(float(params.get("worst_return_quantile", 0.20)))
        return set(by_ticker[by_ticker <= cutoff].index.astype(str))
    if mode == "low_liquidity":
        for col in ["volume", "trades", "signal_score"]:
            if col in signals.columns:
                values = pd.to_numeric(signals[col], errors="coerce")
                if values.notna().any():
                    cutoff = values.quantile(float(params.get("min_volume_quantile", 0.20)))
                    return set(signals.loc[values <= cutoff, "ticker"].astype(str).str.upper())
    if mode == "weak_score" and "signal_score" in signals.columns:
        scores = pd.to_numeric(signals["signal_score"], errors="coerce")
        if scores.notna().any():
            cutoff = scores.quantile(float(params.get("bottom_score_quantile", 0.20)))
            return set(signals.loc[scores <= cutoff, "ticker"].astype(str).str.upper())
    return set()


def _apply_confirmation(signals: pd.DataFrame, signals_by_source: dict[str, pd.DataFrame], sources: list[str]) -> pd.DataFrame:
    out = signals.copy()
    if out.empty:
        return out
    keys = set(zip(out["trade_date"].astype(str), out["ticker"].astype(str).str.upper()))
    for source in sources:
        confirm = signals_by_source.get(str(source).lower(), pd.DataFrame())
        if confirm is None or confirm.empty:
            return out.iloc[0:0].copy()
        confirm_keys = set(zip(confirm["trade_date"].astype(str), confirm["ticker"].astype(str).str.upper()))
        keys &= confirm_keys
    return out[out.apply(lambda r: (str(r["trade_date"]), str(r["ticker"]).upper()) in keys, axis=1)].copy()


def _apply_hypothesis(signals: pd.DataFrame, hypothesis: dict, signals_by_source: dict[str, pd.DataFrame], regimes_df: pd.DataFrame | None = None) -> pd.DataFrame:
    out = signals.copy()
    if out.empty:
        return out
    hyp_type = str(hypothesis.get("hypothesis_type", hypothesis.get("hypothesis_id", ""))).upper()
    params = _params(hypothesis.get("parameters_json"))
    out["ticker"] = out["ticker"].astype(str).str.upper()
    if hyp_type in {"EXCLUDE_HIGH_FRAGILITY_ASSETS", "EXCLUDE_COST_DOMINATED_ASSETS"}:
        remove = _metadata_filter_tickers(out, "weak_score", params)
        return out[~out["ticker"].isin(remove)].copy()
    if hyp_type == "EXCLUDE_LOW_SAMPLE_SIGNALS":
        remove = _metadata_filter_tickers(out, "low_sample", params)
        return out[~out["ticker"].isin(remove)].copy()
    if hyp_type == "LIMIT_SIGNAL_SOURCE":
        return out.sort_values(["trade_date", "ticker"]).reset_index(drop=True).iloc[:: int(params.get("keep_every_n", 2) or 2)].copy()
    if hyp_type == "LIMIT_HIGH_SLIPPAGE_ASSETS":
        remove = _metadata_filter_tickers(out, "low_liquidity", params)
        return out[~out["ticker"].isin(remove)].copy()
    if hyp_type == "BLOCK_DRAWDOWN_CONTRIBUTORS":
        remove = _metadata_filter_tickers(out, "worst_return", params) or _metadata_filter_tickers(out, "weak_score", params)
        return out[~out["ticker"].isin(remove)].copy()
    if hyp_type == "REQUIRE_INTEGRATED_CONFIRMATION":
        return _apply_confirmation(out, signals_by_source, ["integrated"])
    if hyp_type == "REQUIRE_TECHNICAL_CONFIRMATION":
        return _apply_confirmation(out, signals_by_source, ["technical"])
    if hyp_type == "REQUIRE_QUANT_TECHNICAL_AGREEMENT":
        return _apply_confirmation(out, signals_by_source, ["quant", "technical"])
    if hyp_type == "EXCLUDE_EVENT_RISK_SIGNALS":
        if "event_context_type" in out.columns:
            excluded = {str(x).upper() for x in params.get("excluded_event_contexts", [])}
            return out[~out["event_context_type"].astype(str).str.upper().isin(excluded)].copy()
        return out
    if hyp_type == "EXCLUDE_LIQUIDITY_WEAK_REGIME" and regimes_df is not None and not regimes_df.empty:
        excluded = {str(x).upper() for x in params.get("excluded_regimes", [])}
        if excluded:
            regimes = regimes_df.copy()
            regimes["trade_date"] = regimes["trade_date"].astype(str)
            cols = [c for c in ["liquidity_regime", "primary_regime", "risk_regime"] if c in regimes.columns]
            mask = pd.Series(False, index=regimes.index)
            for col in cols:
                mask = mask | regimes[col].astype(str).str.upper().isin(excluded)
            blocked_dates = set(regimes.loc[mask, "trade_date"])
            return out[~out["trade_date"].astype(str).isin(blocked_dates)].copy()
    return out


def _fragility(orders_df: pd.DataFrame, positions_df: pd.DataFrame, equity_df: pd.DataFrame) -> tuple[float, float]:
    asset_df = analyze_pnl_by_asset(orders_df, positions_df, equity_df)
    if asset_df.empty:
        return 100.0, 0.0
    total_trades = int(pd.to_numeric(asset_df.get("trades_count"), errors="coerce").fillna(0).sum())
    total_net_pnl = float(pd.to_numeric(asset_df.get("net_pnl"), errors="coerce").fillna(0).sum())
    cost_drag = float(pd.to_numeric(asset_df.get("total_cost_drag", asset_df.get("cost_drag")), errors="coerce").fillna(0).sum())
    max_drawdown = float(pd.to_numeric(equity_df.get("drawdown"), errors="coerce").fillna(0).min()) if equity_df is not None and not equity_df.empty else 0.0
    top_concentration = float(pd.to_numeric(asset_df.get("contribution_pct"), errors="coerce").abs().fillna(0).max())
    score = calculate_fragility_score(
        {
            "trades_count": total_trades,
            "net_pnl": total_net_pnl,
            "cost_drag": cost_drag,
            "drawdown_contribution": abs(max_drawdown),
            "concentration_pct": top_concentration,
            "win_rate": 0.5,
        }
    )["fragility_score"]
    return float(score), float(cost_drag)


def _run_once(signals: pd.DataFrame, prices: pd.DataFrame, risk: pd.DataFrame | None, start: str, end: str, scenario: dict, hypothesis: dict | None = None) -> dict:
    params = _params(scenario.get("parameters_json"))
    hyp_type = str((hypothesis or {}).get("hypothesis_type", "")).upper()
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
    entry["gross_return"] = (pd.to_numeric(entry["exit_close"], errors="coerce") / pd.to_numeric(entry["entry_close"], errors="coerce")) - 1
    score = pd.to_numeric(entry.get("signal_score"), errors="coerce").fillna(50)
    weight = (score / 100).clip(0.25, 1.0)
    exposure_multiplier = 1.0
    if hyp_type == "REDUCE_VOLATILITY_EXPOSURE":
        exposure_multiplier = 0.5
    elif hyp_type == "LIMIT_ASSET_WEIGHT":
        exposure_multiplier = 0.75
    cost_drag = (float(scenario.get("cost_bps", 10) or 10) + float(scenario.get("slippage_bps", 5) or 5)) / 10000
    entry["net_return"] = (entry["gross_return"].fillna(0) * weight * exposure_multiplier) - cost_drag
    total_return = float(entry["net_return"].mean()) if not entry.empty else 0.0
    series = daily.pivot_table(index="trade_date", columns="ticker", values="close").pct_change(fill_method=None)
    tickers = [t for t in sig["ticker"].unique().tolist() if t in series.columns]
    if tickers:
        curve = (1 + series[tickers].mean(axis=1).fillna(0) * exposure_multiplier).cumprod()
        drawdown = float((curve / curve.cummax() - 1).min()) if not curve.empty else 0.0
    else:
        drawdown = 0.0
    trades = int(len(entry))
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
                "win_rate": float((entry["net_return"] > 0).mean()) if trades else 0.0,
            }
        )["fragility_score"]
    )
    return {
        "return": total_return,
        "drawdown": drawdown,
        "trades": trades,
        "fragility": fragility,
        "cost_drag": cost_drag * trades * 1000,
    }


def _scenario_specs(source: str, cost_scenarios: bool, regimes_df: pd.DataFrame | None) -> list[dict]:
    specs = [{"scenario_name": "BASE_COST", "signal_source": source, "cost_bps": 10, "slippage_bps": 5, "regime_filter": "", "parameters_json": json.dumps({"risk_pct": 0.005, "max_positions": 5})}]
    if cost_scenarios:
        specs.extend(
            [
                {"scenario_name": "HIGH_COST", "signal_source": source, "cost_bps": 20, "slippage_bps": 10, "regime_filter": "", "parameters_json": json.dumps({"risk_pct": 0.005, "max_positions": 5})},
                {"scenario_name": "HIGH_SLIPPAGE", "signal_source": source, "cost_bps": 10, "slippage_bps": 20, "regime_filter": "", "parameters_json": json.dumps({"risk_pct": 0.005, "max_positions": 5})},
            ]
        )
    if regimes_df is not None and not regimes_df.empty and "primary_regime" in regimes_df.columns:
        for regime in regimes_df["primary_regime"].dropna().astype(str).unique().tolist()[:3]:
            specs.append({"scenario_name": f"REGIME_{regime}", "signal_source": source, "cost_bps": 10, "slippage_bps": 5, "regime_filter": regime, "parameters_json": json.dumps({"risk_pct": 0.005, "max_positions": 5})})
    return specs


def run_hypothesis_multi_source_validation(
    hypotheses_df: pd.DataFrame,
    signals_by_source: dict[str, pd.DataFrame],
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    regimes_df: pd.DataFrame | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    train_months: int = 1,
    test_months: int = 1,
    cost_scenarios: bool = True,
) -> pd.DataFrame:
    if hypotheses_df is None or hypotheses_df.empty or prices_df is None or prices_df.empty:
        return pd.DataFrame(columns=VALIDATION_COLUMNS)
    start = str(start_date or prices_df["trade_date"].astype(str).min())
    end = str(end_date or prices_df["trade_date"].astype(str).max())
    windows = create_hypothesis_oos_windows(start, end, train_months=train_months, test_months=test_months)
    if windows.empty:
        return pd.DataFrame(columns=VALIDATION_COLUMNS)
    rows = []
    sources = [s for s, df in (signals_by_source or {}).items() if df is not None and not df.empty]
    for _, hyp_row in hypotheses_df.iterrows():
        hyp = _hypothesis_dict(hyp_row)
        if not bool(hyp.get("can_simulate", True)):
            continue
        for source in sources:
            source_signals_all = signals_by_source[source].copy()
            source_signals_all["signal_source"] = source
            for scenario in _scenario_specs(source, cost_scenarios, regimes_df):
                metrics = []
                useful_cells = 0
                for _, window in windows.iterrows():
                    test_start = str(window["test_start"])
                    test_end = str(window["test_end"])
                    sig = _filter_by_regime(_slice(source_signals_all, test_start, test_end), regimes_df, str(scenario.get("regime_filter", "")))
                    px = _filter_by_regime(_slice(prices_df, test_start, test_end), regimes_df, str(scenario.get("regime_filter", "")))
                    risk = _slice(risk_df, test_start, test_end) if risk_df is not None and not risk_df.empty and "trade_date" in risk_df.columns else risk_df
                    if sig.empty or px.empty:
                        continue
                    useful_cells += 1
                    hyp_sig = _apply_hypothesis(sig, hyp, signals_by_source, regimes_df)
                    base = _run_once(sig, px, risk, test_start, test_end, scenario)
                    after = _run_once(hyp_sig, px, risk, test_start, test_end, scenario, hypothesis=hyp)
                    metrics.append(
                        {
                            "return_delta": after["return"] - base["return"],
                            "drawdown_delta": after["drawdown"] - base["drawdown"],
                            "fragility_delta": after["fragility"] - base["fragility"],
                            "cost_drag_delta": after["cost_drag"] - base["cost_drag"],
                            "trades": after["trades"],
                            "base_trades": base["trades"],
                        }
                    )
                if not metrics:
                    rows.append(
                        {
                            "hypothesis_id": hyp.get("hypothesis_id"),
                            "signal_source": source,
                            "scenario_name": scenario["scenario_name"],
                            "windows_count": int(len(windows)),
                            "useful_cells": 0,
                            "positive_improvement_pct": 0.0,
                            "mean_return_delta": 0.0,
                            "mean_drawdown_delta": 0.0,
                            "mean_fragility_delta": 0.0,
                            "mean_cost_drag_delta": 0.0,
                            "overfitting_flag": True,
                            "cost_sensitivity_flag": False,
                            "regime_instability_flag": bool(scenario.get("regime_filter")),
                            "data_coverage_status": "EVIDENCIA_INSUFICIENTE",
                            "governance_status": "HYPOTHESIS_BLOCKED_LOW_COVERAGE",
                            "metadata_json": json.dumps({"hypothesis": hyp, "scenario": scenario}, ensure_ascii=False, default=str),
                        }
                    )
                    continue
                df = pd.DataFrame(metrics)
                improvement = (df["fragility_delta"] < 0) & (df["return_delta"] >= -0.001) & (df["drawdown_delta"] >= -0.001)
                overfit = bool((df["trades"].mean() < 5) or ((df["base_trades"] > 0) & (df["trades"] < df["base_trades"] * 0.5)).mean() >= 0.5)
                cost_flag = bool(str(scenario["scenario_name"]).upper() in {"HIGH_COST", "HIGH_SLIPPAGE"} and df["return_delta"].mean() < 0)
                regime_flag = bool(scenario.get("regime_filter") and df["return_delta"].mean() < 0)
                coverage_status = "COVERAGE_USEFUL" if useful_cells >= max(1, len(windows) // 2) else "EVIDENCIA_INSUFICIENTE"
                governance = "HYPOTHESIS_ROBUST_FOR_OBSERVATION" if improvement.mean() >= 0.55 and df["fragility_delta"].mean() < 0 and not overfit else "HYPOTHESIS_BLOCKED"
                rows.append(
                    {
                        "hypothesis_id": hyp.get("hypothesis_id"),
                        "signal_source": source,
                        "scenario_name": scenario["scenario_name"],
                        "windows_count": int(len(windows)),
                        "useful_cells": int(useful_cells),
                        "positive_improvement_pct": round(float(improvement.mean()), 4),
                        "mean_return_delta": round(float(df["return_delta"].mean()), 6),
                        "mean_drawdown_delta": round(float(df["drawdown_delta"].mean()), 6),
                        "mean_fragility_delta": round(float(df["fragility_delta"].mean()), 6),
                        "mean_cost_drag_delta": round(float(df["cost_drag_delta"].mean()), 6),
                        "overfitting_flag": overfit,
                        "cost_sensitivity_flag": cost_flag,
                        "regime_instability_flag": regime_flag,
                        "data_coverage_status": coverage_status,
                        "governance_status": governance,
                        "metadata_json": json.dumps({"hypothesis": hyp, "scenario": scenario, "windows": metrics}, ensure_ascii=False, default=str),
                    }
                )
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)
