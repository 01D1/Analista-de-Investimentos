from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.context.connectors.local_csv_connector import load_events as load_csv_events
from src.context.event_model import EVENT_COLUMNS


def load_events(start_date=None, end_date=None, tickers=None, csv_path: str | Path | None = None) -> pd.DataFrame:
    if csv_path:
        events = load_csv_events(start_date=start_date, end_date=end_date, tickers=tickers, csv_path=csv_path)
        if not events.empty:
            events["event_source"] = "manual"
        return events
    default_path = Path("data/events/market_events.csv")
    if default_path.exists():
        events = load_csv_events(start_date=start_date, end_date=end_date, tickers=tickers, csv_path=default_path)
        if not events.empty:
            events["event_source"] = "manual"
        return events
    return pd.DataFrame(columns=EVENT_COLUMNS)

