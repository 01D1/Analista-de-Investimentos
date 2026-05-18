"""Estabilidade de estruturas de opções por vencimento, moneyness e liquidez."""
from __future__ import annotations

import json

import pandas as pd

from src.options.options_backtest_summary import summarize_structure_backtest


def _dte_bucket(value) -> str:
    try:
        dte = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if dte <= 7:
        return "0_7"
    if dte <= 15:
        return "8_15"
    if dte <= 30:
        return "16_30"
    if dte <= 60:
        return "31_60"
    if dte <= 90:
        return "61_90"
    return "90_PLUS"


def _moneyness_from_legs(legs_json: str) -> str:
    try:
        legs = json.loads(legs_json or "[]")
        return str(legs[0].get("moneyness_class") or "UNKNOWN").upper() if legs else "UNKNOWN"
    except (TypeError, ValueError, json.JSONDecodeError):
        return "UNKNOWN"


def _group(df: pd.DataFrame, col: str) -> pd.DataFrame:
    columns = [col, "trades", "mean_net_return", "win_rate", "profit_factor", "avg_cost_drag", "skipped_pct"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for value, group in df.groupby(col, dropna=False):
        s = summarize_structure_backtest(group)
        skipped_pct = s["skipped_count"] / s["total_trades"] * 100 if s["total_trades"] else 0.0
        rows.append(
            {
                col: value,
                "trades": s["total_trades"],
                "mean_net_return": s["mean_net_return"],
                "win_rate": s["win_rate"],
                "profit_factor": s["profit_factor"],
                "avg_cost_drag": s["avg_cost_drag"],
                "skipped_pct": round(float(skipped_pct), 4),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def summarize_by_dte_bucket(results_df: pd.DataFrame) -> pd.DataFrame:
    df = results_df.copy() if results_df is not None else pd.DataFrame()
    if df.empty:
        return _group(df, "dte_bucket")
    df["dte_bucket"] = df.get("dte_entry", pd.Series(index=df.index)).apply(_dte_bucket)
    return _group(df, "dte_bucket")


def summarize_by_moneyness_bucket(results_df: pd.DataFrame) -> pd.DataFrame:
    df = results_df.copy() if results_df is not None else pd.DataFrame()
    if df.empty:
        return _group(df, "moneyness_bucket")
    df["moneyness_bucket"] = df.get("moneyness_class", df.get("legs_json", pd.Series(index=df.index)).apply(_moneyness_from_legs))
    return _group(df, "moneyness_bucket")


def summarize_by_structure_type(results_df: pd.DataFrame) -> pd.DataFrame:
    df = results_df.copy() if results_df is not None else pd.DataFrame()
    return _group(df, "structure_type")


def summarize_by_liquidity_bucket(results_df: pd.DataFrame) -> pd.DataFrame:
    df = results_df.copy() if results_df is not None else pd.DataFrame()
    if df.empty:
        return _group(df, "liquidity_bucket")
    df["liquidity_bucket"] = df.get("execution_quality", pd.Series("DADOS_INSUFICIENTES", index=df.index)).fillna("DADOS_INSUFICIENTES")
    return _group(df, "liquidity_bucket")


def detect_options_stability_issues(summary_df: pd.DataFrame) -> list[str]:
    if summary_df is None or summary_df.empty:
        return ["amostra insuficiente"]
    issues = []
    total = pd.to_numeric(summary_df.get("trades"), errors="coerce").fillna(0).sum()
    if total < 30:
        issues.append("amostra insuficiente")
    if total > 0 and pd.to_numeric(summary_df.get("trades"), errors="coerce").fillna(0).max() / total > 0.7:
        issues.append("performance concentrada em bucket específico")
    if "avg_cost_drag" in summary_df.columns and pd.to_numeric(summary_df["avg_cost_drag"], errors="coerce").fillna(0).mean() > 5:
        issues.append("alto custo médio")
    if "skipped_pct" in summary_df.columns and pd.to_numeric(summary_df["skipped_pct"], errors="coerce").fillna(0).mean() > 40:
        issues.append("muitos skips por liquidez/dados")
    return issues or ["sem alerta relevante"]

