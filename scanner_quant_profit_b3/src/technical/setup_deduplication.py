"""Redução de redundância entre setups técnicos correlatos."""
from __future__ import annotations

import json

import pandas as pd


SETUP_GROUPS = {
    "MOMENTUM": {"BREAKOUT_VOLUME", "MOMENTUM_CONTINUATION", "RANGE_EXPANSION", "RELATIVE_STRENGTH_LEADER"},
    "REVERSAO": {"MEAN_REVERSION", "OVERSOLD_REVERSAL"},
    "TENDENCIA": {"PULLBACK_TREND", "VWAP_RECLAIM"},
}


def _setup_group(setup_type: str) -> str:
    setup = str(setup_type).upper()
    for group, members in SETUP_GROUPS.items():
        if setup in members:
            return group
    return setup


def deduplicate_setups(setups_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if setups_df.empty:
        summary = {"signals_before": 0, "signals_after": 0, "removed_count": 0, "removed_pct": 0.0, "top_redundant_setups": {}}
        return setups_df.copy(), setups_df.copy(), summary
    work = setups_df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce").dt.date.astype(str)
    work["_setup_group"] = work["setup_type"].map(_setup_group)
    group_cols = ["ticker", "trade_date", "setup_direction", "_setup_group"]
    keep_idx = []
    removed_parts = []
    for _, group in work.groupby(group_cols, dropna=False):
        ranked = group.sort_values(["setup_score", "setup_confidence"], ascending=False)
        keep = ranked.iloc[[0]].copy()
        duplicates = ranked.iloc[1:].copy()
        redundant = duplicates["setup_type"].dropna().astype(str).tolist()
        metadata = {"redundant_setups": redundant, "dedupe_group": str(keep.iloc[0]["_setup_group"])}
        keep["metadata_json"] = json.dumps(metadata, ensure_ascii=False)
        keep_idx.append(keep)
        if not duplicates.empty:
            duplicates["metadata_json"] = json.dumps({"canonical_setup_type": str(keep.iloc[0]["setup_type"])}, ensure_ascii=False)
            removed_parts.append(duplicates)
    deduped = pd.concat(keep_idx, ignore_index=True).drop(columns=["_setup_group"], errors="ignore") if keep_idx else work.iloc[0:0]
    removed = pd.concat(removed_parts, ignore_index=True).drop(columns=["_setup_group"], errors="ignore") if removed_parts else work.iloc[0:0].drop(columns=["_setup_group"], errors="ignore")
    summary = summarize_setup_redundancy(setups_df, deduped)
    return deduped, removed, summary


def summarize_setup_redundancy(setups_df: pd.DataFrame, deduped_df: pd.DataFrame) -> dict:
    before = int(len(setups_df))
    after = int(len(deduped_df))
    removed = max(0, before - after)
    top = {}
    if before and "setup_type" in setups_df.columns:
        counts_before = setups_df["setup_type"].value_counts()
        counts_after = deduped_df.get("setup_type", pd.Series(dtype=str)).value_counts()
        diff = (counts_before - counts_after.reindex(counts_before.index).fillna(0)).sort_values(ascending=False)
        top = {str(k): int(v) for k, v in diff.head(5).items() if v > 0}
    by_ticker = {}
    if before and "ticker" in setups_df.columns:
        original = setups_df["ticker"].value_counts()
        final = deduped_df.get("ticker", pd.Series(dtype=str)).value_counts()
        diff = (original - final.reindex(original.index).fillna(0)).sort_values(ascending=False)
        by_ticker = {str(k): int(v) for k, v in diff.head(5).items() if v > 0}
    return {
        "signals_before": before,
        "signals_after": after,
        "removed_count": removed,
        "removed_pct": round((removed / before * 100), 2) if before else 0.0,
        "top_redundant_setups": top,
        "tickers_with_most_redundancy": by_ticker,
    }

