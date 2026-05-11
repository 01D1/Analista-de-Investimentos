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
        ev = events.copy()
        ev["event_date_norm"] = pd.to_datetime(ev["event_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        ev["ticker_norm"] = ev["ticker"].fillna("").astype(str).str.upper()
        ev["is_macro_event"] = ev.apply(_is_macro_event, axis=1)
        event_keys = set(zip(ev["ticker_norm"], ev["event_date_norm"]))
        macro_dates = set(ev.loc[ev["is_macro_event"], "event_date_norm"].dropna().tolist())

        def _covered(row: pd.Series) -> bool:
            date = pd.to_datetime(row.get("trade_date"), errors="coerce")
            if pd.isna(date):
                return False
            date_str = date.strftime("%Y-%m-%d")
            ticker = str(row.get("ticker")).upper()
            return (ticker, date_str) in event_keys or date_str in macro_dates

        signals_with = int(signals.apply(_covered, axis=1).sum())
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


REGIME_COLUMNS = [
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "risk_regime",
]


def _date_str(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


def _is_macro_event(row: pd.Series) -> bool:
    event_type = str(row.get("event_type") or "").upper()
    ticker = str(row.get("ticker") or "").strip()
    return (
        ticker == ""
        or event_type.startswith("MACRO_")
        or event_type in {"JUROS", "CAMBIO", "COMMODITY", "POLITICO", "NOTICIA_GERAL"}
    )


def _attach_regimes(signals: pd.DataFrame, regimes: pd.DataFrame) -> pd.DataFrame:
    out = signals.copy()
    if out.empty:
        return out
    if regimes is None or regimes.empty or "trade_date" not in regimes.columns:
        for col in REGIME_COLUMNS:
            if col not in out.columns:
                out[col] = pd.NA
        return out
    regime_cols = ["trade_date"] + [col for col in REGIME_COLUMNS if col in regimes.columns]
    reg = regimes[regime_cols].copy()
    reg["trade_date"] = _date_str(reg["trade_date"])
    out["trade_date"] = _date_str(out["trade_date"]) if "trade_date" in out.columns else pd.NA
    out = out.merge(reg.drop_duplicates("trade_date"), on="trade_date", how="left", suffixes=("", "_regime"))
    for col in REGIME_COLUMNS:
        alt = f"{col}_regime"
        if col not in out.columns and alt in out.columns:
            out[col] = out[alt]
        elif alt in out.columns:
            out[col] = out[col].combine_first(out[alt])
        if col not in out.columns:
            out[col] = pd.NA
        if alt in out.columns:
            out = out.drop(columns=[alt])
    return out


def _signal_event_flags(signals: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    out = signals.copy()
    if out.empty:
        out["has_event"] = pd.Series(dtype=bool)
        out["matched_event_types"] = pd.Series(dtype=str)
        out["matched_event_sources"] = pd.Series(dtype=str)
        return out
    out["trade_date"] = _date_str(out["trade_date"]) if "trade_date" in out.columns else pd.NA
    out["ticker"] = out.get("ticker", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    if events is None or events.empty or "event_date" not in events.columns:
        out["has_event"] = False
        out["matched_event_types"] = ""
        out["matched_event_sources"] = ""
        return out

    ev = events.copy()
    ev["event_date"] = _date_str(ev["event_date"])
    ev["ticker"] = ev.get("ticker", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    ev["is_macro_event"] = ev.apply(_is_macro_event, axis=1)
    by_date: dict[str, pd.DataFrame] = {date: group for date, group in ev.groupby("event_date", dropna=True)}

    flags = []
    types = []
    sources = []
    for _, row in out.iterrows():
        date = row.get("trade_date")
        ticker = str(row.get("ticker") or "").upper()
        candidates = by_date.get(date, pd.DataFrame())
        if candidates.empty:
            flags.append(False)
            types.append("")
            sources.append("")
            continue
        matched = candidates[(candidates["is_macro_event"]) | (candidates["ticker"].eq(ticker))]
        flags.append(not matched.empty)
        types.append(",".join(sorted(matched.get("event_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())))
        sources.append(",".join(sorted(matched.get("event_source", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())))
    out["has_event"] = flags
    out["matched_event_types"] = types
    out["matched_event_sources"] = sources
    return out


def _dominant_join(series: pd.Series) -> str:
    values = []
    for item in series.dropna().astype(str):
        values.extend([part for part in item.split(",") if part])
    if not values:
        return ""
    return pd.Series(values).value_counts().idxmax()


def calculate_event_coverage_by_regime(
    events_df: pd.DataFrame,
    signals_df: pd.DataFrame,
    regimes_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula cobertura de eventos separada por regime de mercado."""
    columns = [
        "regime_type",
        "regime_value",
        "signals_count",
        "signals_with_event",
        "signals_without_event",
        "signals_with_event_pct",
        "dominant_event_type",
        "dominant_event_source",
        "coverage_quality",
    ]
    signals = signals_df.copy() if signals_df is not None else pd.DataFrame()
    if signals.empty or "trade_date" not in signals.columns:
        return pd.DataFrame(columns=columns)
    signals = _attach_regimes(signals, regimes_df.copy() if regimes_df is not None else pd.DataFrame())
    signals = _signal_event_flags(signals, events_df.copy() if events_df is not None else pd.DataFrame())

    rows = []
    for regime_col in REGIME_COLUMNS:
        if regime_col not in signals.columns:
            continue
        work = signals[signals[regime_col].notna()].copy()
        if work.empty:
            continue
        for regime_value, group in work.groupby(regime_col, dropna=False):
            total = int(len(group))
            with_event = int(group["has_event"].fillna(False).sum())
            pct = with_event / total if total else 0.0
            metrics = {
                "signals_with_event_pct": pct,
                "tickers_with_event_pct": pct,
                "sources_count": int(len(set(",".join(group["matched_event_sources"].dropna().astype(str)).split(",")) - {""})),
                "months_with_events": int(len(set(_month(group.loc[group["has_event"], "trade_date"])))),
            }
            rows.append(
                {
                    "regime_type": regime_col,
                    "regime_value": regime_value,
                    "signals_count": total,
                    "signals_with_event": with_event,
                    "signals_without_event": total - with_event,
                    "signals_with_event_pct": pct,
                    "dominant_event_type": _dominant_join(group.loc[group["has_event"], "matched_event_types"]),
                    "dominant_event_source": _dominant_join(group.loc[group["has_event"], "matched_event_sources"]),
                    "coverage_quality": classify_coverage_quality(metrics),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def classify_regime_event_coverage(coverage_by_regime_df: pd.DataFrame) -> pd.DataFrame:
    """Reclassifica a qualidade de cobertura linha a linha para uma tabela por regime."""
    columns = [
        "regime_type",
        "regime_value",
        "signals_count",
        "signals_with_event",
        "signals_without_event",
        "signals_with_event_pct",
        "dominant_event_type",
        "dominant_event_source",
        "coverage_quality",
    ]
    if coverage_by_regime_df is None or coverage_by_regime_df.empty:
        return pd.DataFrame(columns=columns)
    out = coverage_by_regime_df.copy()
    qualities = []
    for _, row in out.iterrows():
        sources = 1 if str(row.get("dominant_event_source") or "").strip() else 0
        qualities.append(
            classify_coverage_quality(
                {
                    "signals_with_event_pct": float(row.get("signals_with_event_pct") or 0),
                    "tickers_with_event_pct": float(row.get("signals_with_event_pct") or 0),
                    "sources_count": sources,
                    "months_with_events": 1 if float(row.get("signals_with_event_pct") or 0) > 0 else 0,
                }
            )
        )
    out["coverage_quality"] = qualities
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns]
