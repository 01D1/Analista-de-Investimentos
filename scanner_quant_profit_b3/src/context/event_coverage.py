"""Controle de cobertura da base de eventos."""
from __future__ import annotations

from typing import Any

import pandas as pd


def _month(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.to_period("M").astype(str)


def calculate_event_coverage(events_df: pd.DataFrame, signals_df: pd.DataFrame, tickers: list[str] | None = None) -> dict[str, Any]:
    events = events_df.copy() if events_df is not None else pd.DataFrame()
    signals = signals_df.copy() if signals_df is not None else pd.DataFrame()
    if tickers:
        clean = {ticker.upper() for ticker in tickers}
        if "ticker" in events:
            events = events[events["ticker"].astype(str).str.upper().isin(clean)]
        if "ticker" in signals:
            signals = signals[signals["ticker"].astype(str).str.upper().isin(clean)]

    total_signals = int(len(signals))
    event_tickers = set(events.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper())
    signal_tickers = set(signals.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper())
    tickers_with = sorted(signal_tickers & event_tickers)
    tickers_without = sorted(signal_tickers - event_tickers)

    if not signals.empty and {"trade_date", "ticker"}.issubset(signals.columns) and {"event_date", "ticker"}.issubset(events.columns):
        signal_keys = set(zip(signals["ticker"].astype(str).str.upper(), pd.to_datetime(signals["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")))
        event_keys = set(zip(events["ticker"].astype(str).str.upper(), pd.to_datetime(events["event_date"], errors="coerce").dt.strftime("%Y-%m-%d")))
        covered_keys = signal_keys & event_keys
        signals_with = int(signals.apply(lambda row: (str(row.get("ticker")).upper(), pd.to_datetime(row.get("trade_date"), errors="coerce").strftime("%Y-%m-%d")) in covered_keys, axis=1).sum())
    else:
        signals_with = 0

    coverage_by_ticker = {}
    if not signals.empty and "ticker" in signals.columns:
        for ticker, group in signals.groupby(signals["ticker"].astype(str).str.upper()):
            covered = ticker in event_tickers
            coverage_by_ticker[ticker] = 1.0 if covered else 0.0

    coverage_by_month = {}
    if not signals.empty and "trade_date" in signals.columns:
        signal_months = _month(signals["trade_date"])
        event_months = set(_month(events["event_date"])) if "event_date" in events.columns and not events.empty else set()
        for month, count in signal_months.value_counts().items():
            coverage_by_month[month] = {"signals": int(count), "has_events": month in event_months}

    coverage_by_source = events.get("event_source", pd.Series(dtype=str)).fillna("desconhecida").value_counts().to_dict()
    signals_pct = signals_with / total_signals if total_signals else 0.0
    tickers_pct = len(tickers_with) / len(signal_tickers) if signal_tickers else 0.0
    metrics = {
        "total_signals": total_signals,
        "signals_with_coverage": signals_with,
        "signals_without_coverage": total_signals - signals_with,
        "signals_with_event_pct": signals_pct,
        "tickers_with_events": tickers_with,
        "tickers_without_events": tickers_without,
        "tickers_with_event_pct": tickers_pct,
        "dates_with_events": sorted(events.get("event_date", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()),
        "dates_without_events": [],
        "coverage_by_ticker": coverage_by_ticker,
        "coverage_by_month": coverage_by_month,
        "coverage_by_source": coverage_by_source,
        "sources_count": int(len(coverage_by_source)),
        "months_with_events": int(len([m for m, v in coverage_by_month.items() if v["has_events"]])),
    }
    metrics["coverage_quality"] = classify_coverage_quality(metrics)
    return metrics


def classify_coverage_quality(coverage_metrics: dict[str, Any]) -> str:
    signals_pct = float(coverage_metrics.get("signals_with_event_pct", 0) or 0)
    tickers_pct = float(coverage_metrics.get("tickers_with_event_pct", 0) or 0)
    sources = int(coverage_metrics.get("sources_count", 0) or 0)
    months = int(coverage_metrics.get("months_with_events", 0) or 0)
    if signals_pct >= 0.6 and tickers_pct >= 0.6 and sources >= 2 and months >= 2:
        return "COBERTURA_BOA"
    if signals_pct >= 0.3 and tickers_pct >= 0.4 and sources >= 1:
        return "COBERTURA_MEDIA"
    if signals_pct >= 0.1 or tickers_pct >= 0.2 or (sources >= 2 and months >= 2):
        return "COBERTURA_FRACA"
    return "COBERTURA_INSUFICIENTE"
