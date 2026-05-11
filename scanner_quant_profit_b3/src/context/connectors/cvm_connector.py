from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.context.event_model import EVENT_COLUMNS


DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "12_PYTHON" / "pipeline banco completo" / "data" / "qualitative" / "processed"


def _iter_index_files(root: Path, tickers: list[str] | None):
    if not root.exists():
        return []
    if tickers:
        paths = []
        for ticker in tickers:
            paths.extend((root / ticker.upper()).glob("cvm_*index.json"))
        return paths
    return list(root.glob("*/cvm_*index.json"))


def load_events(start_date=None, end_date=None, tickers=None, root_path: str | Path | None = None) -> pd.DataFrame:
    root = Path(root_path) if root_path else DEFAULT_ROOT
    rows = []
    for path in _iter_index_files(root, tickers):
        ticker = path.parent.name.upper()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            data = data.get("items") or data.get("documents") or data.get("eventos") or []
        for item in data if isinstance(data, list) else []:
            event_date = item.get("Data_Referencia") or item.get("Data_Entrega") or item.get("date")
            if not event_date:
                continue
            event_date = pd.to_datetime(event_date, errors="coerce")
            if pd.isna(event_date):
                continue
            event_date_str = event_date.strftime("%Y-%m-%d")
            if start_date and event_date_str < start_date:
                continue
            if end_date and event_date_str > end_date:
                continue
            title = item.get("Assunto") or item.get("Categoria") or item.get("title") or ""
            rows.append(
                {
                    "event_date": event_date_str,
                    "ticker": ticker,
                    "company_name": item.get("Nome_Companhia"),
                    "event_type": item.get("Categoria") or "",
                    "event_source": "cvm",
                    "event_title": title,
                    "event_summary": f"Categoria: {item.get('Categoria','')} Tipo: {item.get('Tipo','')} Assunto: {title}",
                    "event_url": item.get("Link_Download"),
                    "confidence": 0.85,
                    "metadata_json": {"source_file": str(path), "protocolo": item.get("Protocolo_Entrega")},
                }
            )
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)

