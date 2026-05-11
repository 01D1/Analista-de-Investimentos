from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.context.event_model import EVENT_COLUMNS


DEFAULT_PATH = Path(__file__).resolve().parents[4] / "12_PYTHON" / "news_hunter" / "dados" / "calendario_economico.json"


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=EVENT_COLUMNS)


def _importance_score(value: Any) -> tuple[float, float]:
    text = str(value or "").strip().lower()
    if text in {"alta", "alto", "high"}:
        return 0.75, 0.75
    if text in {"media", "média", "medio", "médio", "medium"}:
        return 0.45, 0.6
    if text in {"baixa", "baixo", "low"}:
        return 0.25, 0.45
    return 0.35, 0.5


def _classify_macro_event(title: str, country: str = "") -> str:
    text = f"{title} {country}".lower()
    if any(term in text for term in ["copom", "selic", "juros", "fomc", "fed", "taxa"]):
        return "JUROS"
    if any(term in text for term in ["dólar", "dolar", "câmbio", "cambio", "exchange", "fx"]):
        return "CAMBIO"
    if any(term in text for term in ["petróleo", "petroleo", "oil", "brent", "wti", "minério", "minerio", "commodity"]):
        return "COMMODITY"
    if any(term in text for term in ["eleição", "eleicao", "congresso", "governo", "politic"]):
        return "POLITICO"
    if any(term in text for term in ["eua", "usa", "united states", "payroll", "cpi", "pce"]):
        return "MACRO_EUA"
    if any(term in text for term in ["brasil", "brazil", "ibge", "bcb", "fgv"]):
        return "MACRO_BRASIL"
    return "NOTICIA_GERAL"


def _to_datetime(date_value: Any, time_value: Any) -> str:
    date = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(date):
        return ""
    time_text = str(time_value or "").strip()
    if not time_text or time_text.lower() in {"nan", "none", "não disponível", "nao disponivel"}:
        return date.strftime("%Y-%m-%d")
    dt = pd.to_datetime(f"{date.strftime('%Y-%m-%d')} {time_text}", errors="coerce")
    if pd.isna(dt):
        return date.strftime("%Y-%m-%d")
    return dt.isoformat(timespec="minutes")


def _summary(row: dict[str, Any]) -> str:
    parts = []
    for label, key in [
        ("pais", "pais"),
        ("importancia", "importancia"),
        ("projecao", "projecao"),
        ("anterior", "anterior"),
        ("atual", "atual"),
        ("fonte", "fonte"),
    ]:
        value = row.get(key)
        if value not in (None, ""):
            parts.append(f"{label}: {value}")
    return "; ".join(parts)


def load_events(
    start_date: str | None = None,
    end_date: str | None = None,
    tickers: list[str] | None = None,
    path: str | Path | None = None,
) -> pd.DataFrame:
    """Carrega calendário econômico local no formato padronizado de market_events."""
    calendar_path = Path(path) if path else DEFAULT_PATH
    if not calendar_path.exists():
        return _empty()
    try:
        raw = json.loads(calendar_path.read_text(encoding="utf-8"))
    except Exception:
        return _empty()
    if not raw:
        return _empty()
    if isinstance(raw, dict):
        raw = raw.get("eventos") or raw.get("events") or raw.get("data") or []
    if not isinstance(raw, list):
        return _empty()

    rows = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        date = pd.to_datetime(item.get("data") or item.get("event_date") or item.get("date"), errors="coerce")
        if pd.isna(date):
            continue
        date_str = date.strftime("%Y-%m-%d")
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
        title = str(item.get("indicador") or item.get("titulo") or item.get("event_title") or "").strip()
        country = str(item.get("pais") or item.get("country") or "").strip()
        impact_score, confidence = _importance_score(item.get("importancia") or item.get("importance"))
        event_type = _classify_macro_event(title, country)
        rows.append(
            {
                "event_date": date_str,
                "event_datetime": _to_datetime(date_str, item.get("horario") or item.get("time")),
                "ticker": "",
                "related_tickers": ",".join(tickers or []),
                "company_name": "",
                "event_type": event_type,
                "event_source": "calendario_economico",
                "event_title": title or event_type,
                "event_summary": _summary(item),
                "event_url": "",
                "sector": "",
                "macro_tag": country or event_type,
                "commodity_tag": "COMMODITY" if event_type == "COMMODITY" else "",
                "impact_direction": "INCERTO",
                "impact_score": impact_score,
                "confidence": confidence,
                "metadata_json": {
                    "raw": item,
                    "connector": "macro_calendar_connector",
                },
            }
        )
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)
