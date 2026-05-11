"""Backtest líquido com custos, slippage e filtros de liquidez."""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .execution_costs import classify_execution_quality, estimate_liquidity_penalty


NET_COLUMNS = [
    "net_return_1d",
    "net_return_3d",
    "net_return_5d",
    "net_return_10d",
    "execution_quality",
    "liquidity_penalty",
    "total_cost_pct",
    "total_slippage_pct",
    "is_tradeable",
]


def _empty_like() -> pd.DataFrame:
    return pd.DataFrame(columns=NET_COLUMNS)


def _horizons(df: pd.DataFrame) -> list[int]:
    out = []
    for col in df.columns:
        if col.startswith("future_return_") and col.endswith("d"):
            out.append(int(col.replace("future_return_", "").replace("d", "")))
    return sorted(out)


def apply_execution_costs_to_backtest(
    backtest_df: pd.DataFrame,
    cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
    min_volume: float = 5_000_000,
    min_trades: int = 500,
    only_tradeable: bool = False,
) -> pd.DataFrame:
    if backtest_df is None or backtest_df.empty:
        return _empty_like()

    df = backtest_df.copy()
    total_cost_pct = max(float(cost_bps), 0.0) * 2.0 / 100.0
    total_slippage_pct = max(float(slippage_bps), 0.0) * 2.0 / 100.0

    qualities = []
    penalties = []
    tradeable = []
    for _, row in df.iterrows():
        volume = row.get("volume", row.get("financial_volume", row.get("volume_financeiro", 0)))
        trades = row.get("trades", row.get("negocios", min_trades))
        spread = row.get("spread_pct", None)
        quality = classify_execution_quality(volume, trades=trades, spread_pct=spread)
        penalty = estimate_liquidity_penalty(volume, trades=trades, min_volume=min_volume, min_trades=min_trades)
        is_ok = quality not in {"RUIM", "INVIAVEL"} and penalty["passes_liquidity"]
        qualities.append(quality)
        penalties.append(penalty["penalty_pct"])
        tradeable.append(bool(is_ok))

    df["execution_quality"] = qualities
    df["liquidity_penalty"] = penalties
    df["total_cost_pct"] = round(total_cost_pct, 4)
    df["total_slippage_pct"] = round(total_slippage_pct, 4)
    df["is_tradeable"] = tradeable

    drag = total_cost_pct + total_slippage_pct + df["liquidity_penalty"]
    for horizon in _horizons(df):
        gross_col = f"future_return_{horizon}d"
        net_col = f"net_return_{horizon}d"
        df[net_col] = (pd.to_numeric(df[gross_col], errors="coerce") - drag).round(4)

    if only_tradeable:
        df = df[df["is_tradeable"]].reset_index(drop=True)
    return df


def _hit_rate(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return 0.0
    return round(float((values > 0).mean()), 4)


def _mean(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float(values.mean()), 4) if not values.empty else 0.0


def _best_group(df: pd.DataFrame, group_col: str, metric_col: str) -> str:
    if df.empty or group_col not in df.columns or metric_col not in df.columns:
        return ""
    grouped = df.groupby(group_col)[metric_col].mean(numeric_only=True).sort_values(ascending=False)
    return str(grouped.index[0]) if not grouped.empty else ""


def summarize_net_vs_gross(backtest_df: pd.DataFrame) -> dict:
    if backtest_df is None or backtest_df.empty:
        return {
            "signals": 0,
            "untradeable_signals": 0,
            "removed_by_liquidity": 0,
        }

    df = backtest_df.copy()
    summary = {
        "signals": int(len(df)),
        "tradeable_signals": int(pd.to_numeric(df.get("is_tradeable", False), errors="coerce").fillna(0).sum()),
        "untradeable_signals": int((~df.get("is_tradeable", pd.Series([True] * len(df))).astype(bool)).sum()),
        "removed_by_liquidity": int((pd.to_numeric(df.get("liquidity_penalty", 0), errors="coerce") > 0).sum()),
        "avg_total_cost_pct": _mean(df, "total_cost_pct"),
        "avg_total_slippage_pct": _mean(df, "total_slippage_pct"),
    }
    for horizon in (1, 3, 5, 10):
        gross_col = f"future_return_{horizon}d"
        net_col = f"net_return_{horizon}d"
        summary[f"gross_mean_return_{horizon}d"] = _mean(df, gross_col)
        summary[f"net_mean_return_{horizon}d"] = _mean(df, net_col)
        summary[f"cost_impact_{horizon}d"] = round(
            summary[f"gross_mean_return_{horizon}d"] - summary[f"net_mean_return_{horizon}d"],
            4,
        )
        summary[f"gross_hit_rate_{horizon}d"] = _hit_rate(df[gross_col]) if gross_col in df else 0.0
        summary[f"net_hit_rate_{horizon}d"] = _hit_rate(df[net_col]) if net_col in df else 0.0

    tradeable = df[df.get("is_tradeable", True).astype(bool)] if "is_tradeable" in df else df
    summary["best_net_signal_type"] = _best_group(tradeable, "signal_type", "net_return_5d")
    summary["best_net_score_bucket"] = _best_group(tradeable, "score_bucket", "net_return_5d")
    return summary


def summarize_by_execution_quality(backtest_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["execution_quality", "signals", "mean_net_return_5d", "hit_rate_net_5d", "mean_mae_5d"]
    if backtest_df is None or backtest_df.empty or "execution_quality" not in backtest_df.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for quality, group in backtest_df.groupby("execution_quality", dropna=False):
        rows.append(
            {
                "execution_quality": quality,
                "signals": int(len(group)),
                "mean_net_return_5d": _mean(group, "net_return_5d"),
                "hit_rate_net_5d": _hit_rate(group["net_return_5d"]) if "net_return_5d" in group else 0.0,
                "mean_mae_5d": _mean(group, "mae_5d"),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def generate_net_backtest_report(gross_summary: dict, net_summary: dict | None = None) -> str:
    summary = net_summary or gross_summary or {}
    gross = summary.get("gross_mean_return_5d", 0.0)
    net = summary.get("net_mean_return_5d", 0.0)
    gross_hit = summary.get("gross_hit_rate_5d", 0.0)
    net_hit = summary.get("net_hit_rate_5d", 0.0)
    impact = summary.get("cost_impact_5d", round(gross - net, 4))
    untradeable = summary.get("untradeable_signals", 0)
    total = summary.get("signals", 0) or 1
    pct_untradeable = untradeable / total * 100.0
    best_signal = summary.get("best_net_signal_type") or "indefinido"
    best_bucket = summary.get("best_net_score_bucket") or "indefinido"
    verdict = "sobrevive aos custos" if net > 0 else "perde vantagem após custos"
    return (
        f"Após custos e slippage, o retorno médio D+5 caiu de {gross:.4f}% para {net:.4f}%, "
        f"impacto de {impact:.4f} p.p. A taxa de acerto caiu de {gross_hit:.2%} para {net_hit:.2%}. "
        f"Cerca de {pct_untradeable:.1f}% dos sinais foram classificados como RUIM ou INVIAVEL por liquidez. "
        f"O signal_type líquido mais forte foi {best_signal}, e o score_bucket líquido mais forte foi {best_bucket}. "
        f"A leitura atual indica que a estratégia {verdict}."
    )
