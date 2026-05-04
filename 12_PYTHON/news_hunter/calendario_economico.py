# -*- coding: utf-8 -*-
"""
calendario_economico.py — News Hunter
=======================================
Gerencia o calendário econômico local (JSON manual).
Pode ser evoluído para integrar APIs de calendário no futuro.

Arquivo de dados: dados/calendario_economico.json
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger("news_hunter.calendario")

ARQUIVO_CALENDARIO = Path(__file__).parent / "dados" / "calendario_economico.json"

_EXEMPLO_EVENTOS = [
    {
        "data": "2026-04-24",
        "horario": "09:00",
        "pais": "Brasil",
        "indicador": "IPCA-15",
        "importancia": "alta",
        "projecao": "não disponível",
        "anterior": "não disponível",
        "atual": "não disponível",
        "fonte": "manual"
    },
    {
        "data": "2026-04-24",
        "horario": "09:30",
        "pais": "EUA",
        "indicador": "Pedidos de seguro-desemprego",
        "importancia": "média",
        "projecao": "não disponível",
        "anterior": "não disponível",
        "atual": "não disponível",
        "fonte": "manual"
    },
    {
        "data": "2026-04-29",
        "horario": "19:00",
        "pais": "EUA",
        "indicador": "Decisão de juros do Fed (FOMC)",
        "importancia": "alta",
        "projecao": "não disponível",
        "anterior": "não disponível",
        "atual": "não disponível",
        "fonte": "manual"
    },
    {
        "data": "2026-04-30",
        "horario": "08:30",
        "pais": "Brasil",
        "indicador": "Ata do COPOM",
        "importancia": "alta",
        "projecao": "não disponível",
        "anterior": "não disponível",
        "atual": "não disponível",
        "fonte": "manual"
    }
]


def _garantir_arquivo():
    """Cria o arquivo de calendário com exemplos se não existir."""
    ARQUIVO_CALENDARIO.parent.mkdir(parents=True, exist_ok=True)
    if not ARQUIVO_CALENDARIO.exists():
        ARQUIVO_CALENDARIO.write_text(
            json.dumps(_EXEMPLO_EVENTOS, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info("Calendário criado com eventos de exemplo: %s", ARQUIVO_CALENDARIO)


def carregar_eventos() -> list:
    """Lê todos os eventos do arquivo JSON."""
    _garantir_arquivo()
    try:
        dados = json.loads(ARQUIVO_CALENDARIO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except Exception as exc:
        logger.warning("Erro ao ler calendário: %s", exc)
        return []


def eventos_do_dia(data_ref: date = None) -> list:
    """
    Retorna eventos de uma data específica (padrão: hoje),
    ordenados por horário.
    """
    if data_ref is None:
        data_ref = date.today()

    data_str = data_ref.strftime("%Y-%m-%d")
    todos = carregar_eventos()
    do_dia = [e for e in todos if e.get("data") == data_str]

    # Ordenar por horário
    do_dia.sort(key=lambda e: e.get("horario", "99:99"))
    return do_dia


def formatar_eventos_para_boletim(eventos: list) -> list:
    """
    Recebe lista de eventos e retorna lista de strings formatadas
    prontas para o template.
    Retorna lista vazia se não houver eventos.
    """
    if not eventos:
        return []

    linhas = []
    for e in eventos:
        importancia = e.get("importancia", "").upper()
        icone = {"ALTA": "🔴", "MÉDIA": "🟡", "BAIXA": "🟢"}.get(importancia, "⚪")
        linha = (
            f"{e.get('horario', '--:--')} {icone} "
            f"{e.get('pais', '')} — {e.get('indicador', '')}"
        )
        if e.get("projecao") and e["projecao"] != "não disponível":
            linha += f" | Proj: {e['projecao']}"
        if e.get("anterior") and e["anterior"] != "não disponível":
            linha += f" | Ant: {e['anterior']}"
        if e.get("atual") and e["atual"] != "não disponível":
            linha += f" | Atual: {e['atual']}"
        linhas.append(linha)

    return linhas
