"""Decomposicao por fonte de sinal do deep dive de hipoteses."""
from __future__ import annotations

import pandas as pd


SOURCE_DECOMPOSITION_COLUMNS = [
    "hypothesis_id",
    "source",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "positive_improvement_pct",
    "useful_windows",
    "block_reason",
    "source_classification",
]


def _mode_reason(values: pd.Series) -> str:
    cleaned = values.dropna().astype(str)
    if cleaned.empty:
        return "BLOCKED_BY_LOW_SAMPLE"
    counts = cleaned.value_counts()
    return str(counts.index[0])


def _classify_source(row: pd.Series) -> str:
    useful = int(row.get("useful_windows") or 0)
    if useful <= 0:
        return "SOURCE_INSUFFICIENT_DATA"
    reason = str(row.get("block_reason") or "")
    if reason == "BLOCKED_BY_LOW_SAMPLE":
        return "SOURCE_INSUFFICIENT_DATA"
    positive = float(row.get("positive_improvement_pct") or 0)
    ret = float(row.get("mean_return_delta") or 0)
    frag = float(row.get("mean_fragility_delta") or 0)
    if positive >= 0.6 and ret >= 0 and frag < 0:
        return "SOURCE_SUPPORTS_HYPOTHESIS"
    if ret < 0 or frag > 0 or reason.startswith("BLOCKED_BY_"):
        return "SOURCE_WEAKENS_HYPOTHESIS"
    return "SOURCE_MIXED"


def decompose_hypothesis_by_signal_source(deep_oos_df: pd.DataFrame) -> pd.DataFrame:
    if deep_oos_df is None or deep_oos_df.empty:
        return pd.DataFrame(columns=SOURCE_DECOMPOSITION_COLUMNS)
    df = deep_oos_df.copy()
    for col in ["mean_return_delta", "mean_drawdown_delta", "mean_fragility_delta", "positive_improvement_pct", "trades_count"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)
    if "data_coverage_status" in df.columns:
        df["_useful"] = df["data_coverage_status"].astype(str).eq("COVERAGE_USEFUL") & (df["trades_count"] > 0)
    else:
        df["_useful"] = df["trades_count"] > 0
    grouped = (
        df.groupby(["hypothesis_id", "signal_source"], dropna=False)
        .agg(
            mean_return_delta=("mean_return_delta", "mean"),
            mean_drawdown_delta=("mean_drawdown_delta", "mean"),
            mean_fragility_delta=("mean_fragility_delta", "mean"),
            positive_improvement_pct=("positive_improvement_pct", "mean"),
            useful_windows=("_useful", "sum"),
            block_reason=("block_reason", _mode_reason),
        )
        .reset_index()
        .rename(columns={"signal_source": "source"})
    )
    grouped["source_classification"] = grouped.apply(_classify_source, axis=1)
    return grouped[SOURCE_DECOMPOSITION_COLUMNS].sort_values(["hypothesis_id", "source"]).reset_index(drop=True)
