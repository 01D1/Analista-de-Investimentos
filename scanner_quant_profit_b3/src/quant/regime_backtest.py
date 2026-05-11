"""Resumo de backtest por regime de mercado."""
from __future__ import annotations

from typing import Any

import pandas as pd


REGIME_GROUPS = ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"]


def _mean(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float(values.mean()), 4) if not values.empty else 0.0


def _hit(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float((values > 0).mean() * 100.0), 4) if not values.empty else 0.0


def _best_group(df: pd.DataFrame, group_col: str, metric_col: str) -> str:
    if df.empty or group_col not in df.columns or metric_col not in df.columns:
        return ""
    grouped = df.groupby(group_col)[metric_col].mean(numeric_only=True).sort_values(ascending=False)
    return str(grouped.index[0]) if not grouped.empty else ""


def _top_asset_concentration(df: pd.DataFrame) -> float:
    if df.empty or "ticker" not in df.columns:
        return 0.0
    shares = df["ticker"].astype(str).value_counts(normalize=True)
    return round(float(shares.iloc[0] * 100.0), 4) if not shares.empty else 0.0


def _execution_rank(value: Any) -> float:
    order = {"INVIAVEL": 0, "RUIM": 1, "ACEITAVEL": 2, "ACEITÁVEL": 2, "BOA": 3, "EXCELENTE": 4}
    return float(order.get(str(value or "").upper(), 2))


def _robustness(row: dict) -> str:
    if row["signals_count"] < 30:
        return "AMOSTRA_INSUFICIENTE"
    if row["mean_net_return_5d"] > 0 and row["hit_rate_5d"] >= 52 and row["tradeable_pct"] >= 70:
        return "ROBUSTO"
    if row["mean_net_return_5d"] > 0:
        return "PROMISSOR"
    return "FRAGIL"


def summarize_backtest_by_regime(backtest_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "regime_type",
        "regime_value",
        "signals_count",
        "mean_gross_return_5d",
        "mean_net_return_5d",
        "hit_rate_5d",
        "tradeable_pct",
        "top_asset_concentration_pct",
        "best_signal_type",
        "best_score_bucket",
        "mean_drawdown_5d",
        "avg_execution_quality",
        "robustness_class",
    ]
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for regime_col in REGIME_GROUPS:
        if regime_col not in backtest_df.columns:
            continue
        for value, group in backtest_df.groupby(regime_col, dropna=False):
            tradeable = pd.to_numeric(group.get("is_tradeable"), errors="coerce")
            row = {
                "regime_type": regime_col,
                "regime_value": value,
                "signals_count": int(len(group)),
                "mean_gross_return_5d": _mean(group, "future_return_5d"),
                "mean_net_return_5d": _mean(group, "net_return_5d"),
                "hit_rate_5d": _hit(group, "net_return_5d" if "net_return_5d" in group.columns else "future_return_5d"),
                "tradeable_pct": round(float(tradeable.fillna(0).mean() * 100.0), 4) if "is_tradeable" in group.columns else 0.0,
                "top_asset_concentration_pct": _top_asset_concentration(group),
                "best_signal_type": _best_group(group, "signal_type", "net_return_5d"),
                "best_score_bucket": _best_group(group, "score_bucket", "net_return_5d"),
                "mean_drawdown_5d": _mean(group, "mae_5d" if "mae_5d" in group.columns else "max_adverse_excursion_5d"),
                "avg_execution_quality": round(float(group.get("execution_quality", pd.Series(dtype=str)).map(_execution_rank).mean()), 4)
                if "execution_quality" in group.columns
                else 0.0,
            }
            row["robustness_class"] = _robustness(row)
            rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def compare_regime_performance(summary_df: pd.DataFrame, min_samples: int = 30) -> dict:
    if summary_df is None or summary_df.empty:
        return {"best_regimes": [], "weak_regimes": [], "insufficient_regimes": [], "liquidity_risk_regimes": []}
    primary = summary_df[summary_df["regime_type"] == "primary_regime"].copy()
    if primary.empty:
        primary = summary_df.copy()
    sufficient = primary[pd.to_numeric(primary["signals_count"], errors="coerce") >= min_samples]
    return {
        "best_regimes": sufficient[sufficient["mean_net_return_5d"] > 0].sort_values("mean_net_return_5d", ascending=False)["regime_value"].astype(str).tolist(),
        "weak_regimes": sufficient[sufficient["mean_net_return_5d"] <= 0].sort_values("mean_net_return_5d")["regime_value"].astype(str).tolist(),
        "insufficient_regimes": primary[primary["signals_count"] < min_samples]["regime_value"].astype(str).tolist(),
        "liquidity_risk_regimes": primary[primary["tradeable_pct"] < 50]["regime_value"].astype(str).tolist(),
    }


def generate_regime_report(regime_summary: pd.DataFrame) -> str:
    comparison = compare_regime_performance(regime_summary)
    best = ", ".join(comparison["best_regimes"]) or "nenhum regime"
    weak = ", ".join(comparison["weak_regimes"]) or "nenhum regime"
    insufficient = ", ".join(comparison["insufficient_regimes"]) or "nenhum regime"
    return (
        f"O backtest por regimes indica melhor desempenho líquido em {best}. "
        f"Os regimes com falha ou retorno líquido negativo foram {weak}. "
        f"Regimes com amostra insuficiente: {insufficient}. "
        "Essa leitura não aprova thresholds automaticamente."
    )
