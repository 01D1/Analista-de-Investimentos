"""
News Bridge — lê os outputs do news_hunter.

Formatos suportados (em ordem de prioridade):
  1. Arquivo combinado:  <outputs_dir>/news_latest.json
       {"PETR4": {"headline": "...", "date": "...", "source": "..."}, ...}

  2. Por ticker (JSON):  <outputs_dir>/news_<TICKER>_<YYYYMMDD>.json
       {"headlines": [{"title": "...", "date": "...", "source": "..."}, ...]}

  3. Por ticker (CSV):   <outputs_dir>/news_<TICKER>_<YYYYMMDD>.csv
       colunas: date, title, source

Somente leitura — nunca altera o projeto de origem.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Arquivo combinado (news_latest.json)
# ---------------------------------------------------------------------------

def _load_combined(outputs_dir: Path) -> dict[str, dict]:
    """Carrega news_latest.json se existir. Retorna dict {TICKER: {...}}."""
    path = outputs_dir / "news_latest.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Arquivo por ticker
# ---------------------------------------------------------------------------

def _find_latest_news_file(outputs_dir: Path, ticker: str) -> Optional[Path]:
    """Retorna o arquivo de notícias mais recente para o ticker."""
    for ext in ("json", "csv"):
        candidates = sorted(outputs_dir.glob(f"news_{ticker}_*.{ext}"), reverse=True)
        if candidates:
            return candidates[0]
    return None


def _read_json_news(path: Path) -> Optional[dict]:
    """Lê arquivo JSON de notícias e retorna a manchete mais recente."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    headlines = data.get("headlines", [])
    if not headlines:
        return None

    # Ordena por data decrescente se houver campo date
    headlines_sorted = sorted(
        headlines,
        key=lambda x: x.get("date", ""),
        reverse=True,
    )
    top = headlines_sorted[0]
    return {
        "headline": str(top.get("title", top.get("headline", ""))),
        "headline_date": str(top.get("date", "")),
        "headline_source": str(top.get("source", "")),
    }


def _read_csv_news(path: Path) -> Optional[dict]:
    """Lê arquivo CSV de notícias e retorna a manchete mais recente."""
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except Exception:
        try:
            df = pd.read_csv(path, encoding="latin-1", sep=";")
        except Exception:
            return None

    if df.empty:
        return None

    # Detecta coluna de título
    title_col = next((c for c in df.columns if c.lower() in ("title", "titulo", "headline", "manchete")), None)
    date_col = next((c for c in df.columns if c.lower() in ("date", "data", "published_at")), None)
    source_col = next((c for c in df.columns if c.lower() in ("source", "fonte", "veiculo")), None)

    if title_col is None:
        return None

    df = df.sort_values(date_col, ascending=False) if date_col else df
    row = df.iloc[0]
    return {
        "headline": str(row[title_col]),
        "headline_date": str(row[date_col]) if date_col else "",
        "headline_source": str(row[source_col]) if source_col else "",
    }


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

def get_news(ticker: str, outputs_dir: str | Path) -> dict:
    """
    Retorna dict com manchete mais recente do ticker, ou {} se não encontrada.

    Retorno:
        {"headline": "...", "headline_date": "YYYY-MM-DD", "headline_source": "..."}
    """
    outputs_dir = Path(outputs_dir)
    if not outputs_dir.exists():
        return {}

    # 1. Arquivo combinado
    combined = _load_combined(outputs_dir)
    if ticker in combined:
        entry = combined[ticker]
        return {
            "headline": str(entry.get("headline", entry.get("title", ""))),
            "headline_date": str(entry.get("date", "")),
            "headline_source": str(entry.get("source", "")),
        }

    # 2. Arquivo por ticker
    file_path = _find_latest_news_file(outputs_dir, ticker)
    if file_path is None:
        return {}

    if file_path.suffix == ".json":
        return _read_json_news(file_path) or {}
    elif file_path.suffix == ".csv":
        return _read_csv_news(file_path) or {}

    return {}


def get_news_batch(tickers: list[str], outputs_dir: str | Path) -> dict[str, dict]:
    """Retorna dict {ticker: news_dict} para uma lista de tickers."""
    outputs_dir = Path(outputs_dir)
    combined = _load_combined(outputs_dir) if outputs_dir.exists() else {}

    result: dict[str, dict] = {}
    for t in tickers:
        if t in combined:
            entry = combined[t]
            result[t] = {
                "headline": str(entry.get("headline", entry.get("title", ""))),
                "headline_date": str(entry.get("date", "")),
                "headline_source": str(entry.get("source", "")),
            }
        else:
            result[t] = get_news(t, outputs_dir)
    return result
