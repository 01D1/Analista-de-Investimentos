"""Vinculo entre sinais quantitativos e eventos locais de mercado."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database


LINK_TYPES = {
    "SAME_DAY",
    "BEFORE_SIGNAL",
    "AFTER_SIGNAL",
    "MACRO_CONTEXT",
    "SECTOR_CONTEXT",
    "COMMODITY_CONTEXT",
    "NO_EVENT",
}


def _date(value: Any) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce").normalize()


def _related_contains(related: Any, ticker: str) -> bool:
    tokens = [item.strip().upper() for item in str(related or "").replace(",", ";").split(";") if item.strip()]
    return ticker.upper() in tokens


def _is_macro_event(event: pd.Series) -> bool:
    return bool(str(event.get("macro_tag") or "").strip()) or str(event.get("event_type") or "").upper().startswith("MACRO") or str(event.get("event_type") or "").upper() in {"JUROS", "CAMBIO", "POLITICO"}


def _candidate_events(signal: pd.Series, events: pd.DataFrame, before: int, after: int) -> pd.DataFrame:
    if events is None or events.empty:
        return pd.DataFrame()
    ticker = str(signal.get("ticker") or "").upper()
    signal_date = _date(signal.get("trade_date") or signal.get("signal_date"))
    if pd.isna(signal_date):
        return pd.DataFrame()
    work = events.copy()
    work["_event_date"] = pd.to_datetime(work.get("event_date"), errors="coerce").dt.normalize()
    work = work.dropna(subset=["_event_date"])
    work["_days_from_event"] = (signal_date - work["_event_date"]).dt.days
    work = work[(work["_days_from_event"] >= -after) & (work["_days_from_event"] <= before)]
    if work.empty:
        return work

    direct = work["ticker"].astype(str).str.upper().eq(ticker)
    related = work.get("related_tickers", pd.Series("", index=work.index)).apply(lambda value: _related_contains(value, ticker))
    macro = work.apply(_is_macro_event, axis=1)
    sector = work.get("event_type", pd.Series("", index=work.index)).astype(str).str.upper().eq("SETORIAL") & (direct | related)
    commodity = work.get("event_type", pd.Series("", index=work.index)).astype(str).str.upper().eq("COMMODITY") & (direct | related)
    return work[direct | related | macro | sector | commodity].copy()


def _link_type(event: pd.Series, days_from_event: int) -> str:
    event_type = str(event.get("event_type") or "").upper()
    if event_type == "SETORIAL":
        return "SECTOR_CONTEXT"
    if event_type == "COMMODITY":
        return "COMMODITY_CONTEXT"
    if _is_macro_event(event):
        return "MACRO_CONTEXT"
    if days_from_event == 0:
        return "SAME_DAY"
    if days_from_event > 0:
        return "BEFORE_SIGNAL"
    return "AFTER_SIGNAL"


def classify_signal_event_context(row: dict | pd.Series) -> str:
    has_event = bool(row.get("has_event"))
    if not has_event:
        return "TECNICO_SEM_EVENTO"
    link_type = str(row.get("link_type") or "").upper()
    signal_type = str(row.get("signal_type") or "").upper()
    direction = str(row.get("impact_direction") or "").upper()
    impact = pd.to_numeric(pd.Series([row.get("event_impact_score", row.get("impact_score"))]), errors="coerce").iloc[0]
    impact = 0.0 if pd.isna(impact) else float(impact)
    if link_type == "MACRO_CONTEXT":
        return "EVENTO_MACRO"
    if link_type == "SECTOR_CONTEXT":
        return "EVENTO_SETORIAL"
    bullish_signal = any(token in signal_type for token in ["FORÇA", "FORCA", "ROMPIMENTO"])
    bearish_signal = "FRAQUEZA" in signal_type
    if (direction == "NEGATIVO" and bullish_signal) or (direction == "POSITIVO" and bearish_signal):
        return "EVENTO_CONTRA_SINAL"
    if link_type == "SAME_DAY" and impact >= 0.7:
        return "MOVIMENTO_EVENT_DRIVEN"
    return "TECNICO_COM_CONFIRMACAO_EVENTO"


def _no_event_row(signal: pd.Series) -> dict[str, Any]:
    out = signal.to_dict()
    out.update(
        {
            "has_event": False,
            "event_id": None,
            "event_date": None,
            "event_type": None,
            "event_impact_score": None,
            "impact_direction": None,
            "days_from_event": None,
            "event_title": None,
            "link_type": "NO_EVENT",
            "event_confidence": None,
        }
    )
    out["event_context_type"] = classify_signal_event_context(out)
    return out


def link_events_to_signals(
    signals_df: pd.DataFrame,
    events_df: pd.DataFrame,
    window_days_before: int = 1,
    window_days_after: int = 1,
) -> pd.DataFrame:
    if signals_df is None or signals_df.empty:
        return pd.DataFrame()
    events = events_df.copy() if events_df is not None else pd.DataFrame()
    rows = []
    for _, signal in signals_df.iterrows():
        candidates = _candidate_events(signal, events, window_days_before, window_days_after)
        if candidates.empty:
            rows.append(_no_event_row(signal))
            continue
        candidates["_abs_days"] = candidates["_days_from_event"].abs()
        candidates["_impact"] = pd.to_numeric(candidates.get("impact_score"), errors="coerce").fillna(0.0)
        candidates["_link_type"] = candidates.apply(lambda event: _link_type(event, int(event.get("_days_from_event"))), axis=1)
        priority = {"SAME_DAY": 0, "SECTOR_CONTEXT": 1, "COMMODITY_CONTEXT": 1, "BEFORE_SIGNAL": 2, "AFTER_SIGNAL": 3, "MACRO_CONTEXT": 4}
        candidates["_priority"] = candidates["_link_type"].map(priority).fillna(9)
        event = candidates.sort_values(["_abs_days", "_priority", "_impact"], ascending=[True, True, False]).iloc[0]
        days = int(event.get("_days_from_event"))
        out = signal.to_dict()
        out.update(
            {
                "has_event": True,
                "event_id": event.get("id", event.get("event_id")),
                "event_date": event.get("event_date"),
                "event_type": event.get("event_type"),
                "event_impact_score": event.get("impact_score"),
                "impact_direction": event.get("impact_direction"),
                "days_from_event": days,
                "event_title": event.get("event_title"),
                "link_type": _link_type(event, days),
                "event_confidence": event.get("confidence"),
            }
        )
        out["event_context_type"] = classify_signal_event_context(out)
        rows.append(out)
    return pd.DataFrame(rows)


def summarize_event_linkage(linked_df: pd.DataFrame) -> dict[str, Any]:
    if linked_df is None or linked_df.empty:
        return {
            "total_signals": 0,
            "signals_with_same_day_event": 0,
            "signals_with_near_event": 0,
            "signals_without_event": 0,
            "events_by_type": {},
            "mean_return_with_event": 0.0,
            "mean_return_without_event": 0.0,
            "hit_rate_with_event": 0.0,
            "hit_rate_without_event": 0.0,
            "return_by_event_type": {},
            "return_by_impact_direction": {},
        }
    df = linked_df.copy()
    has_event = df.get("has_event", False).astype(bool)
    ret = pd.to_numeric(df.get("net_return_5d", df.get("future_return_5d")), errors="coerce")
    return {
        "total_signals": int(len(df)),
        "signals_with_same_day_event": int((df.get("link_type") == "SAME_DAY").sum()),
        "signals_with_near_event": int(has_event.sum()),
        "signals_without_event": int((~has_event).sum()),
        "events_by_type": df.loc[has_event, "event_type"].value_counts(dropna=True).to_dict() if "event_type" in df else {},
        "mean_return_with_event": round(float(ret[has_event].mean()), 4) if ret[has_event].notna().any() else 0.0,
        "mean_return_without_event": round(float(ret[~has_event].mean()), 4) if ret[~has_event].notna().any() else 0.0,
        "hit_rate_with_event": round(float((ret[has_event].dropna() > 0).mean()), 4) if ret[has_event].notna().any() else 0.0,
        "hit_rate_without_event": round(float((ret[~has_event].dropna() > 0).mean()), 4) if ret[~has_event].notna().any() else 0.0,
        "return_by_event_type": ret.groupby(df.get("event_type")).mean().round(4).dropna().to_dict() if "event_type" in df else {},
        "return_by_impact_direction": ret.groupby(df.get("impact_direction")).mean().round(4).dropna().to_dict() if "impact_direction" in df else {},
    }


def save_signal_event_links(linked_df: pd.DataFrame, db_path: str | Path) -> int:
    if linked_df is None or linked_df.empty:
        return 0
    init_database(db_path, verbose=False)
    rows = linked_df[linked_df.get("has_event", False).astype(bool)].copy()
    if rows.empty:
        return 0
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        for _, row in rows.iterrows():
            cur.execute(
                """
                INSERT INTO signal_event_links (
                    signal_id, backtest_result_id, ticker, signal_date, event_id, event_date,
                    event_type, event_impact_score, days_from_event, link_type, confidence, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("signal_id"),
                    row.get("id"),
                    row.get("ticker"),
                    row.get("trade_date", row.get("signal_date")),
                    row.get("event_id"),
                    row.get("event_date"),
                    row.get("event_type"),
                    row.get("event_impact_score"),
                    row.get("days_from_event"),
                    row.get("link_type"),
                    row.get("event_confidence"),
                    json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                ),
            )
        con.commit()
    return int(len(rows))
