"""Histórico e tendências do snapshot integrado por ativo."""
from __future__ import annotations

import pandas as pd


HISTORY_COLUMNS = [
    "created_at",
    "integrated_score",
    "integrated_status",
    "governance_status",
    "data_quality_score",
    "upside_pct",
    "technical_score_final",
    "quant_score",
    "option_structure_score",
    "primary_regime",
    "event_context_type",
]


def _trend(series: pd.Series, threshold: float = 2.0) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 2:
        return "INSUFICIENTE"
    delta = float(values.iloc[-1] - values.iloc[0])
    if delta > threshold:
        return "MELHORANDO"
    if delta < -threshold:
        return "PIORANDO"
    return "ESTAVEL"


def build_asset_history(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df is None or df.empty or not ticker:
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    work = df[df["ticker"].astype(str).str.upper() == str(ticker).upper()].copy()
    if work.empty:
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    work["created_at_dt"] = pd.to_datetime(work.get("created_at"), errors="coerce")
    work = work.sort_values(["created_at_dt", "id"], na_position="first")
    out = pd.DataFrame(
        {
            "created_at": work.get("created_at"),
            "integrated_score": work.get("integrated_score"),
            "integrated_status": work.get("integrated_status"),
            "governance_status": work.get("integrated_governance_status"),
            "data_quality_score": work.get("data_quality_score"),
            "upside_pct": work.get("upside_pct"),
            "technical_score_final": work.get("technical_score_final"),
            "quant_score": work.get("quant_score"),
            "option_structure_score": work.get("option_structure_score"),
            "primary_regime": work.get("primary_regime"),
            "event_context_type": work.get("event_context_type"),
        }
    )
    return out[HISTORY_COLUMNS]


def summarize_asset_history(history_df: pd.DataFrame) -> dict:
    if history_df is None or history_df.empty:
        return {
            "snapshots_count": 0,
            "first_snapshot_at": None,
            "latest_snapshot_at": None,
            "status_changes_count": 0,
            "governance_blocks_count": 0,
            "avg_integrated_score": 0.0,
            "min_integrated_score": 0.0,
            "max_integrated_score": 0.0,
            "latest_status": None,
            "latest_governance_status": None,
            "data_quality_trend": "INSUFICIENTE",
            "score_trend": "INSUFICIENTE",
            "most_common_status": None,
        }
    score = pd.to_numeric(history_df.get("integrated_score"), errors="coerce")
    statuses = history_df.get("integrated_status", pd.Series(dtype=str)).astype(str)
    gov = history_df.get("governance_status", pd.Series(dtype=str)).astype(str)
    return {
        "snapshots_count": int(len(history_df)),
        "first_snapshot_at": history_df.iloc[0].get("created_at"),
        "latest_snapshot_at": history_df.iloc[-1].get("created_at"),
        "status_changes_count": int((statuses != statuses.shift()).sum() - 1) if len(statuses) else 0,
        "governance_blocks_count": int(gov.str.contains("BLOCKED|BLOQUEADO", case=False, na=False).sum()),
        "avg_integrated_score": round(float(score.mean()), 4) if score.notna().any() else 0.0,
        "min_integrated_score": round(float(score.min()), 4) if score.notna().any() else 0.0,
        "max_integrated_score": round(float(score.max()), 4) if score.notna().any() else 0.0,
        "latest_status": history_df.iloc[-1].get("integrated_status"),
        "latest_governance_status": history_df.iloc[-1].get("governance_status"),
        "data_quality_trend": _trend(history_df.get("data_quality_score", pd.Series(dtype=float))),
        "score_trend": _trend(history_df.get("integrated_score", pd.Series(dtype=float))),
        "most_common_status": statuses.mode().iloc[0] if not statuses.mode().empty else None,
    }
