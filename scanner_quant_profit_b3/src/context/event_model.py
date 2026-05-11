"""Modelo padronizado para eventos de mercado e notícias locais."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd


EVENT_COLUMNS = [
    "event_id",
    "event_date",
    "event_datetime",
    "ticker",
    "related_tickers",
    "company_name",
    "event_type",
    "event_source",
    "event_title",
    "event_summary",
    "event_url",
    "sector",
    "macro_tag",
    "commodity_tag",
    "impact_direction",
    "impact_score",
    "confidence",
    "created_at",
    "metadata_json",
]

EVENT_TYPES = {
    "RESULTADO",
    "FATO_RELEVANTE",
    "COMUNICADO",
    "GUIDANCE",
    "DIVIDENDOS",
    "MUDANCA_GESTAO",
    "M_A",
    "REGULATORIO",
    "JUDICIAL",
    "MACRO_BRASIL",
    "MACRO_EUA",
    "JUROS",
    "CAMBIO",
    "COMMODITY",
    "SETORIAL",
    "POLITICO",
    "RATING",
    "RECOMENDACAO_ANALISTA",
    "NOTICIA_GERAL",
    "DESCONHECIDO",
}

IMPACT_DIRECTIONS = {"POSITIVO", "NEGATIVO", "NEUTRO", "INCERTO"}

EVENT_TYPE_ALIASES = {
    "FATO RELEVANTE": "FATO_RELEVANTE",
    "MUDANCA GESTAO": "MUDANCA_GESTAO",
    "MUDANCA_GESTÃO": "MUDANCA_GESTAO",
    "M&A": "M_A",
    "MA": "M_A",
    "RECOMENDACAO ANALISTA": "RECOMENDACAO_ANALISTA",
    "RECOMENDAÇÃO ANALISTA": "RECOMENDACAO_ANALISTA",
    "NOTICIA": "NOTICIA_GERAL",
    "NOTÍCIA": "NOTICIA_GERAL",
}

IMPACT_ALIASES = {
    "POSITIVA": "POSITIVO",
    "POSITIVE": "POSITIVO",
    "NEGATIVA": "NEGATIVO",
    "NEGATIVE": "NEGATIVO",
    "NEUTRAL": "NEUTRO",
    "UNKNOWN": "INCERTO",
}


def normalize_event_type(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", "_")
    text = " ".join(text.split())
    text = EVENT_TYPE_ALIASES.get(text, text.replace(" ", "_"))
    return text if text in EVENT_TYPES else "DESCONHECIDO"


def normalize_impact_direction(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", "_")
    text = " ".join(text.split())
    text = IMPACT_ALIASES.get(text, text.replace(" ", "_"))
    return text if text in IMPACT_DIRECTIONS else "INCERTO"


def clamp_0_1(value: Any, default: float = 0.0) -> float:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return default
    return max(0.0, min(1.0, float(number)))


def normalize_event_date(value: Any) -> str | None:
    date = pd.to_datetime(value, errors="coerce")
    if pd.isna(date):
        return None
    return date.strftime("%Y-%m-%d")


def normalize_event_record(record: dict[str, Any]) -> dict[str, Any]:
    out = {col: record.get(col) for col in EVENT_COLUMNS}
    out["event_date"] = normalize_event_date(out.get("event_date") or out.get("event_datetime"))
    ticker = out.get("ticker")
    related = out.get("related_tickers")
    out["ticker"] = "" if pd.isna(ticker) else str(ticker or "").strip().upper()
    out["related_tickers"] = "" if pd.isna(related) else str(related or "").strip().upper()
    out["event_type"] = normalize_event_type(out.get("event_type"))
    out["impact_direction"] = normalize_impact_direction(out.get("impact_direction"))
    out["impact_score"] = clamp_0_1(out.get("impact_score"), default=0.0)
    out["confidence"] = clamp_0_1(out.get("confidence"), default=0.5)
    out["created_at"] = out.get("created_at") or datetime.now().isoformat(timespec="seconds")
    metadata = out.get("metadata_json")
    if isinstance(metadata, dict):
        out["metadata_json"] = json.dumps(metadata, ensure_ascii=False, default=str)
    elif metadata is None:
        out["metadata_json"] = "{}"
    return out
