"""Diagnostico de fragilidade por setor."""
from __future__ import annotations

import pandas as pd

from src.paper.fragility_score import add_fragility_columns


def _num(group: pd.DataFrame, col: str, default=0) -> pd.Series:
    if col in group.columns:
        return pd.to_numeric(group[col], errors="coerce").fillna(default)
    return pd.Series([default] * len(group), index=group.index)


def attach_sector_to_paper_results(results_df: pd.DataFrame, sector_map_df: pd.DataFrame | None) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame()
    out = results_df.copy()
    if "ticker" not in out.columns:
        out["ticker"] = "UNKNOWN"
    out["ticker"] = out["ticker"].astype(str).str.upper()
    if sector_map_df is None or sector_map_df.empty or "ticker" not in sector_map_df.columns:
        out["sector"] = "UNKNOWN"
        return out
    sectors = sector_map_df.copy()
    sectors["ticker"] = sectors["ticker"].astype(str).str.upper()
    if "sector" not in sectors.columns:
        sectors["sector"] = "UNKNOWN"
    return out.merge(sectors[["ticker", "sector"]].drop_duplicates("ticker"), on="ticker", how="left").assign(sector=lambda df: df["sector"].fillna("UNKNOWN"))


def analyze_pnl_by_sector(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["sector", "net_pnl", "trades", "win_rate", "drawdown_contribution", "concentration_pct", "cost_drag", "fragility_score", "fragility_class", "metadata_json"]
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=columns)
    work = results_df.copy()
    if "sector" not in work.columns:
        work["sector"] = "UNKNOWN"
    rows = []
    total = max(float(pd.to_numeric(work.get("net_pnl", work.get("total_return", 0)), errors="coerce").abs().sum()), 1.0)
    for sector, group in work.groupby("sector", dropna=False):
        pnl = pd.to_numeric(group.get("net_pnl", group.get("total_return", 0)), errors="coerce").fillna(0)
        rows.append(
            {
                "sector": sector,
                "net_pnl": round(float(pnl.sum()), 6),
                "trades": int(pd.to_numeric(group.get("trades_count", group.get("trades", 0)), errors="coerce").fillna(0).sum()),
                "win_rate": round(float(pd.to_numeric(group.get("win_rate"), errors="coerce").fillna(0).mean()), 6),
                "drawdown_contribution": round(abs(float(_num(group, "max_drawdown").min())), 6),
                "concentration_pct": round(float(abs(pnl.sum()) / total), 6),
                "cost_drag": round(float((_num(group, "cost_drag") if "cost_drag" in group.columns else _num(group, "total_cost_drag")).sum()), 6),
                "metadata_json": "{}",
            }
        )
    return add_fragility_columns(pd.DataFrame(rows))[columns]
