"""Decomposicao por ativo do deep dive de hipoteses."""
from __future__ import annotations

import pandas as pd


ASSET_DECOMPOSITION_COLUMNS = [
    "hypothesis_id",
    "ticker",
    "trades_count",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "positive_improvement_pct",
    "cost_sensitivity",
    "slippage_sensitivity",
    "contribution_to_blockage",
    "asset_classification",
]


def _classify_asset(row: pd.Series) -> str:
    trades = int(row.get("trades_count") or 0)
    if trades <= 0:
        return "ASSET_INSUFFICIENT_DATA"
    if bool(row.get("cost_sensitivity")) or bool(row.get("slippage_sensitivity")):
        return "ASSET_HURTS_HYPOTHESIS"
    if float(row.get("mean_return_delta") or 0) >= 0 and float(row.get("mean_fragility_delta") or 0) < 0 and float(row.get("positive_improvement_pct") or 0) >= 0.55:
        return "ASSET_HELPS_HYPOTHESIS"
    if float(row.get("mean_return_delta") or 0) < 0 or float(row.get("mean_fragility_delta") or 0) > 0:
        return "ASSET_HURTS_HYPOTHESIS"
    return "ASSET_NEUTRAL"


def decompose_hypothesis_by_asset(deep_oos_df: pd.DataFrame) -> pd.DataFrame:
    """Resume condicoes de fragilidade por ticker.

    A linha `TODOS` e removida porque representa o agregado, nao um ativo.
    """
    if deep_oos_df is None or deep_oos_df.empty:
        return pd.DataFrame(columns=ASSET_DECOMPOSITION_COLUMNS)
    df = deep_oos_df.copy()
    df = df[df.get("ticker", pd.Series(dtype=str)).astype(str).str.upper().ne("TODOS")]
    if df.empty:
        return pd.DataFrame(columns=ASSET_DECOMPOSITION_COLUMNS)
    for col in ["trades_count", "mean_return_delta", "mean_drawdown_delta", "mean_fragility_delta", "positive_improvement_pct"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)
    for flag_col in ["cost_sensitivity_flag", "slippage_sensitivity_flag"]:
        if flag_col not in df.columns:
            df[flag_col] = False
    grouped = (
        df.groupby(["hypothesis_id", "ticker"], dropna=False)
        .agg(
            trades_count=("trades_count", "sum"),
            mean_return_delta=("mean_return_delta", "mean"),
            mean_drawdown_delta=("mean_drawdown_delta", "mean"),
            mean_fragility_delta=("mean_fragility_delta", "mean"),
            positive_improvement_pct=("positive_improvement_pct", "mean"),
            cost_sensitivity=("cost_sensitivity_flag", "max"),
            slippage_sensitivity=("slippage_sensitivity_flag", "max"),
        )
        .reset_index()
    )
    blockers = df[df["block_reason"].astype(str).ne("NO_CLEAR_BLOCKER")]
    if not blockers.empty:
        counts = blockers.groupby(["hypothesis_id", "ticker"]).size().rename("block_count").reset_index()
        total = blockers.groupby("hypothesis_id").size().rename("total_blocks").reset_index()
        grouped = grouped.merge(counts, on=["hypothesis_id", "ticker"], how="left").merge(total, on="hypothesis_id", how="left")
        grouped["contribution_to_blockage"] = (grouped["block_count"].fillna(0) / grouped["total_blocks"].replace(0, pd.NA)).fillna(0).round(4)
    else:
        grouped["contribution_to_blockage"] = 0.0
    grouped["asset_classification"] = grouped.apply(_classify_asset, axis=1)
    return grouped[ASSET_DECOMPOSITION_COLUMNS].sort_values(["hypothesis_id", "contribution_to_blockage", "ticker"], ascending=[True, False, True]).reset_index(drop=True)
