from __future__ import annotations

import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table


OPTION_COLUMNS = [
    "ticker",
    "option_available",
    "best_option_structure_type",
    "option_structure_score",
    "option_oos_governance_status",
    "option_liquidity_score",
    "option_execution_quality",
    "option_explanation",
]


def load_latest_option_candidates(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    cols = ["underlying", "structure_type", "structure_score", "liquidity_score", "explanation", "governance_status"]
    df = read_table(db_path, "option_structure_candidates", cols, order_by="id DESC", limit=5000)
    if df.empty:
        return empty(OPTION_COLUMNS)
    df = df.rename(columns={"underlying": "ticker"})
    df = filter_tickers(df, tickers)
    if df.empty:
        return empty(OPTION_COLUMNS)
    ranked = df.sort_values(["ticker", "structure_score", "liquidity_score"], ascending=[True, False, False]).groupby("ticker", as_index=False).first()
    out = ranked.rename(
        columns={
            "structure_type": "best_option_structure_type",
            "structure_score": "option_structure_score",
            "liquidity_score": "option_liquidity_score",
            "explanation": "option_explanation",
            "governance_status": "option_oos_governance_status",
        }
    )
    out["option_available"] = 1
    out["option_execution_quality"] = pd.NA
    for col in OPTION_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[OPTION_COLUMNS]


def load_latest_option_walk_forward_status(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    cols = ["governance_status", "robustness_class"]
    runs = read_table(db_path, "option_walk_forward_runs", cols, order_by="id DESC", limit=1)
    status = runs.iloc[0]["governance_status"] if not runs.empty else pd.NA
    return pd.DataFrame({"ticker": tickers or [pd.NA], "option_oos_governance_status": status})


def load_option_governance_by_underlying(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    options = load_latest_option_candidates(db_path, tickers)
    if options.empty:
        return empty(["ticker", "option_oos_governance_status"])
    return options[["ticker", "option_oos_governance_status"]]

