"""Execucao de experimentos simulados a partir de hipoteses de fragilidade."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd

from src.paper.fragility_by_asset import analyze_pnl_by_asset
from src.paper.fragility_score import calculate_fragility_score
from src.paper.simulator import run_paper_simulation


def _hypothesis_dict(hypothesis: Any) -> dict:
    if isinstance(hypothesis, pd.Series):
        return hypothesis.to_dict()
    if is_dataclass(hypothesis):
        return asdict(hypothesis)
    return dict(hypothesis)


def _metadata(hypothesis: dict) -> dict:
    raw = hypothesis.get("metadata_json") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}


def apply_investigation_hypothesis_to_signals(signals_df: pd.DataFrame, hypothesis) -> pd.DataFrame:
    """Aplica a hipotese somente sobre a base de sinais simulada."""
    signals = signals_df.copy() if signals_df is not None else pd.DataFrame()
    if signals.empty:
        return signals
    hyp = _hypothesis_dict(hypothesis)
    hyp_type = str(hyp.get("hypothesis_type", "")).upper()
    target = str(hyp.get("target", "")).upper()
    if "ticker" in signals.columns:
        signals["ticker"] = signals["ticker"].astype(str).str.upper()
    if "signal_source" in signals.columns:
        signals["signal_source"] = signals["signal_source"].astype(str).str.lower()

    if hyp_type in {"EXCLUDE_ASSET", "LIMIT_ASSET_COST", "BLOCK_DRAWDOWN_CONTRIBUTOR"} and target:
        return signals[signals["ticker"] != target].copy()
    if hyp_type == "EXCLUDE_SIGNAL_SOURCE" and target:
        return signals[signals["signal_source"] != target.lower()].copy()
    if hyp_type == "LIMIT_SIGNAL_SOURCE" and target:
        # Investigacao conservadora: reduz a fonte mantendo uma amostra alternada
        # por data/ticker, sem alterar score ou ranking original.
        scoped = signals["signal_source"] == target.lower()
        keep_scoped = signals[scoped].sort_values(["trade_date", "ticker"]).reset_index(drop=True)
        keep_scoped = keep_scoped.iloc[::2]
        out = pd.concat([signals[~scoped], keep_scoped], ignore_index=True)
        sort_cols = [c for c in ["trade_date", "ticker"] if c in out.columns]
        return out.sort_values(sort_cols) if sort_cols else out
    if hyp_type == "EXCLUDE_HIGH_FRAGILITY":
        tickers = [str(t).upper() for t in _metadata(hyp).get("tickers", [])]
        if tickers:
            return signals[~signals["ticker"].isin(tickers)].copy()
    return signals


def _summarize_fragility(orders_df: pd.DataFrame, positions_df: pd.DataFrame, equity_df: pd.DataFrame) -> dict:
    asset_df = analyze_pnl_by_asset(orders_df, positions_df, equity_df)
    total_trades = int(pd.to_numeric(asset_df.get("trades_count"), errors="coerce").fillna(0).sum()) if not asset_df.empty else 0
    total_net_pnl = float(pd.to_numeric(asset_df.get("net_pnl"), errors="coerce").fillna(0).sum()) if not asset_df.empty else 0.0
    cost_drag = float(pd.to_numeric(asset_df.get("total_cost_drag", asset_df.get("cost_drag")), errors="coerce").fillna(0).sum()) if not asset_df.empty else 0.0
    max_drawdown = float(pd.to_numeric(equity_df.get("drawdown"), errors="coerce").fillna(0).min()) if equity_df is not None and not equity_df.empty else 0.0
    top_concentration = float(pd.to_numeric(asset_df.get("contribution_pct"), errors="coerce").abs().fillna(0).max()) if not asset_df.empty else 0.0
    score = calculate_fragility_score(
        {
            "trades_count": total_trades,
            "net_pnl": total_net_pnl,
            "cost_drag": cost_drag,
            "drawdown_contribution": abs(max_drawdown),
            "concentration_pct": top_concentration,
            "win_rate": 0.5,
        }
    )
    return {
        "fragility_score_after": score["fragility_score"],
        "fragility_class_after": score["fragility_class"],
        "cost_drag": cost_drag,
        "total_net_pnl": total_net_pnl,
    }


def run_investigation_simulation(
    base_run_config: dict,
    hypothesis,
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
) -> dict:
    """Roda um experimento de paper trading apenas em simulacao."""
    hyp = _hypothesis_dict(hypothesis)
    hyp_type = str(hyp.get("hypothesis_type", "")).upper()
    adjusted_signals = apply_investigation_hypothesis_to_signals(signals_df, hyp)
    config = dict(base_run_config or {})
    if hyp_type == "DISABLE_REBALANCING":
        config["enable_rebalancing"] = False
    if hyp_type == "REDUCE_REBALANCING":
        config["enable_rebalancing"] = False
    if hyp_type == "REDUCE_VOLATILITY_EXPOSURE":
        config["risk_pct"] = max(float(config.get("risk_pct", 0.005) or 0.005) * 0.5, 0.0005)
        config["max_positions"] = max(1, int(config.get("max_positions", 5) or 5) - 1)

    result = run_paper_simulation(
        adjusted_signals,
        prices_df,
        risk_df=risk_df,
        start_date=config.get("start_date"),
        end_date=config.get("end_date"),
        capital=float(config.get("capital", config.get("capital_initial", 100000)) or 100000),
        max_positions=int(config.get("max_positions", 5) or 5),
        risk_pct=float(config.get("risk_pct", 0.005) or 0.005),
        cost_bps=float(config.get("cost_bps", 10) or 10),
        slippage_bps=float(config.get("slippage_bps", 5) or 5),
        stop_loss_pct=config.get("stop_loss_pct", 0.03),
        take_profit_pct=config.get("take_profit_pct", 0.10),
        trailing_stop_pct=config.get("trailing_stop_pct", 0.04),
        daily_loss_limit_pct=config.get("daily_loss_limit_pct", 0.02),
        enable_rebalancing=bool(config.get("enable_rebalancing", False)),
        rebalance_frequency=str(config.get("rebalance_frequency", "WEEKLY")),
        use_regime_adjustment=bool(config.get("use_regime_adjustment", False)),
    )
    summary = result.get("performance_summary", {}).copy()
    fragility_summary = _summarize_fragility(result.get("orders_df", pd.DataFrame()), result.get("positions_df", pd.DataFrame()), result.get("equity_curve_df", pd.DataFrame()))
    summary.update(fragility_summary)
    return {
        "hypothesis_id": hyp.get("hypothesis_id"),
        "simulated_return": float(summary.get("total_return", 0) or 0),
        "simulated_drawdown": float(summary.get("max_drawdown", 0) or 0),
        "simulated_trades": int(summary.get("trades_count", 0) or 0),
        "simulated_win_rate": float(summary.get("win_rate", 0) or 0),
        "simulated_profit_factor": float(summary.get("profit_factor", 0) or 0),
        "fragility_score_after": float(summary.get("fragility_score_after", 100) or 100),
        "fragility_class_after": summary.get("fragility_class_after", "DADOS_INSUFICIENTES"),
        "cost_drag": float(summary.get("cost_drag", 0) or 0),
        "governance_status": summary.get("status", "INSUFFICIENT_DATA"),
        "metadata_json": json.dumps({"hypothesis": hyp, "signals_after": int(len(adjusted_signals)), "summary": summary}, ensure_ascii=False),
        "result": result,
    }
