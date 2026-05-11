"""Classificador heurístico de eventos sem dependência externa."""
from __future__ import annotations

from typing import Any


TYPE_KEYWORDS = [
    ("FATO_RELEVANTE", ["fato relevante"]),
    ("RESULTADO", ["resultado", "lucro", "prejuízo", "prejuizo", "ebitda", "balanço", "balanco", "itr", "dfp"]),
    ("GUIDANCE", ["guidance", "projeção", "projecao", "prévia", "previa"]),
    ("DIVIDENDOS", ["dividendos", "jcp", "juros sobre capital", "proventos"]),
    ("MUDANCA_GESTAO", ["renúncia", "renuncia", "eleição", "eleicao", "diretor", "presidente", "conselho"]),
    ("M_A", ["fusão", "fusao", "aquisição", "aquisicao", "incorporação", "incorporacao", "venda de ativo", "desinvestimento"]),
    ("REGULATORIO", ["cvm", "ofício", "oficio", "regulatório", "regulatorio", "b3"]),
    ("JUDICIAL", ["judicial", "arbitragem", "liminar", "tutela", "processo"]),
    ("JUROS", ["selic", "copom", "juros", "banco central"]),
    ("CAMBIO", ["câmbio", "cambio", "dólar", "dolar"]),
    ("COMMODITY", ["petróleo", "petroleo", "brent", "minério", "minerio", "soja", "commodity"]),
    ("SETORIAL", ["setor", "setorial"]),
    ("POLITICO", ["governo", "congresso", "político", "politico", "eleição presidencial"]),
    ("RATING", ["rating", "upgrade", "downgrade", "agência de risco", "agencia de risco"]),
    ("RECOMENDACAO_ANALISTA", ["recomendação", "recomendacao", "preço-alvo", "preco-alvo"]),
    ("COMUNICADO", ["comunicado", "informa", "esclarecimento"]),
]

POSITIVE_WORDS = [
    "lucro acima",
    "acima do esperado",
    "guidance elevado",
    "recompra",
    "dividendos maiores",
    "upgrade",
    "aprova",
    "crescimento",
    "recorde",
]

NEGATIVE_WORDS = [
    "prejuízo",
    "prejuizo",
    "fraude",
    "renúncia",
    "renuncia",
    "investigação",
    "investigacao",
    "guidance cortado",
    "downgrade",
    "queda",
    "atraso",
    "inadimplência",
    "inadimplencia",
]


def _text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def classify_event_type(title: str, summary: str | None = None, source: str | None = None) -> str:
    text = _text(title, summary, source)
    if "macro" in text and "eua" in text:
        return "MACRO_EUA"
    if "macro" in text and "brasil" in text:
        return "MACRO_BRASIL"
    for event_type, keywords in TYPE_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return event_type
    return "NOTICIA_GERAL" if text.strip() else "DESCONHECIDO"


def estimate_event_impact(title: str, summary: str | None = None, event_type: str | None = None) -> dict[str, float | str]:
    text = _text(title, summary)
    positive = sum(1 for word in POSITIVE_WORDS if word in text)
    negative = sum(1 for word in NEGATIVE_WORDS if word in text)
    if positive > negative:
        return {"impact_direction": "POSITIVO", "impact_score": min(1.0, 0.45 + 0.15 * positive), "confidence": min(1.0, 0.55 + 0.1 * positive)}
    if negative > positive:
        return {"impact_direction": "NEGATIVO", "impact_score": min(1.0, 0.45 + 0.15 * negative), "confidence": min(1.0, 0.55 + 0.1 * negative)}
    if event_type in {"RESULTADO", "FATO_RELEVANTE", "GUIDANCE", "M_A"}:
        return {"impact_direction": "INCERTO", "impact_score": 0.45, "confidence": 0.45}
    return {"impact_direction": "NEUTRO", "impact_score": 0.2, "confidence": 0.35}

