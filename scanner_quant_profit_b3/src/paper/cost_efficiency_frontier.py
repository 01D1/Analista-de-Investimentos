"""Fronteira eficiente custo-retorno-drawdown."""
from __future__ import annotations

import pandas as pd


def _better_or_equal(a, b) -> bool:
    return (
        float(a.get("cost_reduction_pct", 0) or 0) >= float(b.get("cost_reduction_pct", 0) or 0)
        and float(a.get("return_delta", 0) or 0) >= float(b.get("return_delta", 0) or 0)
        and float(a.get("drawdown_delta", 0) or 0) >= float(b.get("drawdown_delta", 0) or 0)
        and float(a.get("turnover_delta", 0) or 0) <= float(b.get("turnover_delta", 0) or 0)
    )


def _strictly_better(a, b) -> bool:
    return (
        float(a.get("cost_reduction_pct", 0) or 0) > float(b.get("cost_reduction_pct", 0) or 0)
        or float(a.get("return_delta", 0) or 0) > float(b.get("return_delta", 0) or 0)
        or float(a.get("drawdown_delta", 0) or 0) > float(b.get("drawdown_delta", 0) or 0)
        or float(a.get("turnover_delta", 0) or 0) < float(b.get("turnover_delta", 0) or 0)
    )


def calculate_cost_efficiency_frontier(variants_df: pd.DataFrame) -> pd.DataFrame:
    """Identificar variantes não-dominadas."""
    columns = ["variant_id", "is_efficient", "dominated_by", "frontier_rank", "efficiency_reason"]
    if variants_df is None or variants_df.empty:
        return pd.DataFrame(columns=columns)
    work = variants_df.copy().reset_index(drop=True)
    rows = []
    for idx, row in work.iterrows():
        dominated_by = ""
        for jdx, other in work.iterrows():
            if idx == jdx:
                continue
            if _better_or_equal(other, row) and _strictly_better(other, row):
                dominated_by = str(other.get("variant_id", "UNKNOWN"))
                break
        efficient = dominated_by == ""
        rows.append(
            {
                "variant_id": row.get("variant_id"),
                "is_efficient": bool(efficient),
                "dominated_by": dominated_by,
                "frontier_rank": None,
                "efficiency_reason": "Fronteira eficiente: variante não dominada." if efficient else f"Dominada por {dominated_by}.",
            }
        )
    frontier = pd.DataFrame(rows)
    merged = work.merge(frontier, on="variant_id", how="left")
    efficient = merged[merged["is_efficient"].astype(bool)].copy()
    if not efficient.empty:
        sort_cols = [c for c in ["efficiency_score", "cost_reduction_pct", "return_delta", "drawdown_delta"] if c in efficient.columns]
        efficient = efficient.sort_values(sort_cols, ascending=False)
        ranks = {variant: i + 1 for i, variant in enumerate(efficient["variant_id"].tolist())}
        merged["frontier_rank"] = merged["variant_id"].map(ranks)
    return merged


def summarize_efficiency_frontier(frontier_df: pd.DataFrame) -> dict:
    if frontier_df is None or frontier_df.empty:
        return {"variants_count": 0, "efficient_count": 0, "best_variant_id": None, "summary": "Evidência insuficiente."}
    efficient = frontier_df[frontier_df.get("is_efficient", pd.Series(False, index=frontier_df.index)).astype(bool)]
    best = efficient.sort_values("frontier_rank").iloc[0].to_dict() if not efficient.empty and "frontier_rank" in efficient.columns else {}
    return {
        "variants_count": int(len(frontier_df)),
        "efficient_count": int(len(efficient)),
        "best_variant_id": best.get("variant_id"),
        "summary": f"{len(efficient)} de {len(frontier_df)} variantes ficaram na fronteira eficiente.",
    }
