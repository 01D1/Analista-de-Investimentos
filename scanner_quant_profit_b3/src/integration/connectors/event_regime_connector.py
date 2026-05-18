from __future__ import annotations

import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table


EVENT_COLUMNS = ["ticker", "has_recent_event", "event_type", "event_context_type", "event_impact_score", "event_coverage_quality", "event_governance_status"]
REGIME_COLUMNS = ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime", "regime_governance_status"]


def load_latest_event_context(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    cols = ["ticker", "event_date", "event_type", "impact_score"]
    events = read_table(db_path, "market_events", cols, order_by="event_date DESC, id DESC", limit=5000)
    events = filter_tickers(events, tickers)
    base = tickers or events.get("ticker", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
    if not base:
        return empty(EVENT_COLUMNS)
    latest = events.sort_values(["ticker", "event_date"], ascending=[True, False]).groupby("ticker", as_index=False).first() if not events.empty else pd.DataFrame({"ticker": base})
    out = pd.DataFrame({"ticker": [str(t).upper() for t in base]}).merge(latest, on="ticker", how="left")
    for col in ["event_type", "impact_score"]:
        if col not in out.columns:
            out[col] = pd.NA
    out["has_recent_event"] = out["event_type"].notna().astype(int)
    out["event_context_type"] = out["has_recent_event"].map({1: "EVENTO_RECENTE", 0: "TECNICO_SEM_EVENTO"})
    out["event_impact_score"] = pd.to_numeric(out.get("impact_score"), errors="coerce")
    coverage = read_table(db_path, "event_coverage_runs", ["coverage_quality"], order_by="id DESC", limit=1)
    out["event_coverage_quality"] = coverage.iloc[0]["coverage_quality"] if not coverage.empty else pd.NA
    out["event_governance_status"] = out["event_coverage_quality"].map(lambda x: "EVENT_COVERAGE_OK" if str(x).upper() in {"COBERTURA_BOA", "COBERTURA_MEDIA"} else "EVENT_COVERAGE_WEAK")
    for col in EVENT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[EVENT_COLUMNS]


def load_latest_regime_context(db_path) -> pd.DataFrame:
    regimes = read_table(db_path, "market_regime_daily", ["trade_date", "primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"], order_by="trade_date DESC, id DESC", limit=1)
    if regimes.empty:
        return empty(REGIME_COLUMNS)
    row = regimes.iloc[0].to_dict()
    row["regime_governance_status"] = "REGIME_RISK_ELEVATED" if str(row.get("risk_regime", "")).upper() == "RISCO_ELEVADO" else "REGIME_OK"
    return pd.DataFrame([row])[REGIME_COLUMNS]


def load_event_governance(db_path, tickers: list[str] | None = None) -> pd.DataFrame:
    events = load_latest_event_context(db_path, tickers)
    if events.empty:
        return empty(["ticker", "event_governance_status"])
    return events[["ticker", "event_governance_status"]]
