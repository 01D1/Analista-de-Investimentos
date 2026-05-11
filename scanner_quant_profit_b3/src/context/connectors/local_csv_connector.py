from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.context.event_importer import load_events_from_csv
from src.context.event_model import EVENT_COLUMNS


def load_events(start_date=None, end_date=None, tickers=None, csv_path: str | Path | None = None) -> pd.DataFrame:
    if not csv_path or not Path(csv_path).exists():
        return pd.DataFrame(columns=EVENT_COLUMNS)
    events = load_events_from_csv(csv_path)
    events["event_source"] = events.get("event_source").fillna("csv").replace("", "csv")
    if start_date:
        events = events[events["event_date"] >= start_date]
    if end_date:
        events = events[events["event_date"] <= end_date]
    if tickers:
        clean = {ticker.upper() for ticker in tickers}
        events = events[events["ticker"].astype(str).str.upper().isin(clean) | events["ticker"].astype(str).eq("")]
    return events.reset_index(drop=True)

