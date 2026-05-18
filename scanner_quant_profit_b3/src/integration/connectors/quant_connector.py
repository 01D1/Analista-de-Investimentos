from __future__ import annotations

import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table


QUANT_COLUMNS = [
    "ticker",
    "trade_date",
    "market_price",
    "company_name",
    "quant_score",
    "quant_signal_type",
    "quant_signal_confidence",
    "quant_explanation",
]


def load_latest_quant_signals(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    cols = ["ticker", "trade_date", "score_final", "signal_type", "signal_confidence", "explanation", "metadata_json"]
    df = read_table(db_path, "historical_backtest_results", cols, order_by="trade_date DESC, id DESC", limit=10000)
    df = filter_tickers(df, tickers)
    if df.empty:
        return empty(QUANT_COLUMNS)
    latest = df.sort_values(["ticker", "trade_date"], ascending=[True, False]).groupby("ticker", as_index=False).first()
    out = latest.rename(columns={"score_final": "quant_score", "signal_type": "quant_signal_type", "signal_confidence": "quant_signal_confidence", "explanation": "quant_explanation"})
    for col in QUANT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[QUANT_COLUMNS]


def load_quant_governance_by_ticker(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    cols = ["source_type", "candidate_name", "governance_status", "created_at"]
    reviews = read_table(db_path, "governance_reviews", cols, order_by="id DESC", limit=200)
    if reviews.empty:
        base = tickers or []
        return pd.DataFrame({"ticker": base, "quant_governance_status": pd.NA})
    status = reviews.iloc[0].get("governance_status")
    base = tickers or []
    return pd.DataFrame({"ticker": base or [pd.NA], "quant_governance_status": status})


def load_latest_score_calibration(db_path) -> pd.DataFrame:
    return read_table(db_path, "score_calibration_runs", ["id", "created_at", "total_assets", "mean_score_final", "inflation_alert"], order_by="id DESC", limit=1)

