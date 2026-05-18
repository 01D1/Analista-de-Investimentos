from __future__ import annotations

import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table


TECHNICAL_COLUMNS = [
    "ticker",
    "trade_date",
    "technical_score_final",
    "technical_status",
    "top_technical_setup",
    "technical_setup_score",
    "technical_setup_confidence",
    "technical_governance_status",
    "technical_explanation",
]

TECHNICAL_WF_COLUMNS = ["technical_oos_status", "technical_wf_robustness", "technical_wf_positive_windows_pct"]


def load_latest_technical_signals(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    setup_cols = ["ticker", "trade_date", "setup_type", "setup_score", "setup_confidence", "technical_status", "governance_status", "explanation"]
    setups = read_table(db_path, "technical_setup_signals", setup_cols, order_by="id DESC", limit=5000)
    setups = filter_tickers(setups, tickers)
    if setups.empty:
        return empty(TECHNICAL_COLUMNS)
    setups = setups.sort_values(["ticker", "trade_date", "setup_score", "setup_confidence"], ascending=[True, False, False, False])
    latest = setups.groupby("ticker", as_index=False).first()
    out = latest.rename(
        columns={
            "setup_type": "top_technical_setup",
            "setup_score": "technical_setup_score",
            "setup_confidence": "technical_setup_confidence",
            "governance_status": "technical_governance_status",
            "explanation": "technical_explanation",
        }
    )
    feature_cols = ["ticker", "trade_date", "technical_score_final", "technical_status"]
    features = read_table(db_path, "technical_feature_snapshots", feature_cols, order_by="id DESC", limit=5000)
    features = filter_tickers(features, tickers)
    if not features.empty:
        features = features.sort_values(["ticker", "trade_date"], ascending=[True, False]).groupby("ticker", as_index=False).first()
        out = out.drop(columns=[c for c in ["technical_score_final", "technical_status"] if c in out.columns], errors="ignore")
        out = out.merge(features, on="ticker", how="left", suffixes=("", "_feature"))
        out["trade_date"] = out["trade_date"].combine_first(out.get("trade_date_feature"))
        out = out.drop(columns=["trade_date_feature"], errors="ignore")
    for col in TECHNICAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[TECHNICAL_COLUMNS]


def load_latest_technical_walk_forward_status(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    cols = ["id", "robustness_class", "governance_status", "positive_windows_pct"]
    runs = read_table(db_path, "technical_walk_forward_runs", cols, order_by="id DESC", limit=1)
    if runs.empty:
        return empty(["ticker", *TECHNICAL_WF_COLUMNS])
    ticker_values = tickers or []
    if not ticker_values:
        ticker_values = [pd.NA]
    rows = []
    row = runs.iloc[0]
    for ticker in ticker_values:
        rows.append(
            {
                "ticker": ticker,
                "technical_oos_status": row.get("governance_status"),
                "technical_wf_robustness": row.get("robustness_class"),
                "technical_wf_positive_windows_pct": row.get("positive_windows_pct"),
            }
        )
    return pd.DataFrame(rows)


def load_technical_governance_by_ticker(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    signals = load_latest_technical_signals(db_path, tickers)
    if signals.empty:
        return empty(["ticker", "technical_governance_status"])
    return signals[["ticker", "technical_governance_status"]]

