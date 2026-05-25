"""
src/utils/ticker_aliases.py — Loader de corporate actions / ticker aliases
==========================================================================

Lê config/ticker_aliases.yaml e expõe interface pública para:
  - identificar tickers legados (LEGACY_TICKER)
  - resolver ticker atual a partir de ticker legado
  - listar todos os corporate actions registrados

Interface pública
-----------------
    LEGACY_TICKERS : frozenset[str]
        Conjunto de todos os tickers legados (active=false por corporate action).

    is_legacy_ticker(ticker: str) -> bool
        Retorna True se o ticker está marcado como legado.

    resolve_ticker(ticker: str) -> str
        Se ticker é legado, retorna o successor. Senão, retorna o próprio ticker.

    get_corporate_actions() -> list[dict]
        Lista completa de corporate actions do YAML.

    get_alias_record(legacy_ticker: str) -> dict | None
        Retorna o registro completo para um ticker legado, ou None.

Regras
------
- NUNCA calcular valuation
- NUNCA criar fair_value
- NUNCA alterar banco (este módulo é read-only)
- Tickers legados → coverage_status='legacy_ticker' → bloqueados pelo router (D087)
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Caminho padrão do YAML ─────────────────────────────────────────────────────

_DEFAULT_YAML = Path(__file__).resolve().parents[2] / "config" / "ticker_aliases.yaml"


# ── Loader (cached) ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_yaml(path: str = str(_DEFAULT_YAML)) -> list[dict]:
    """Carrega e faz cache do YAML. Retorna lista de registros."""
    try:
        import yaml
    except ImportError as e:
        log.warning("PyYAML não disponível: %s — ticker_aliases desabilitado", e)
        return []

    p = Path(path)
    if not p.exists():
        log.warning("ticker_aliases.yaml não encontrado em %s — nenhum alias registrado", p)
        return []

    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    records = data.get("ticker_aliases", [])
    log.debug("ticker_aliases: %d registros carregados de %s", len(records), p)
    return records


# ── Interface pública ──────────────────────────────────────────────────────────

def get_corporate_actions(yaml_path: Optional[str] = None) -> list[dict]:
    """
    Retorna lista completa de corporate actions registrados no YAML.

    Parameters
    ----------
    yaml_path : str | None
        Caminho alternativo para o YAML. Se None, usa o padrão do projeto.
    """
    path = yaml_path or str(_DEFAULT_YAML)
    return list(_load_yaml(path))


def get_alias_record(legacy_ticker: str, yaml_path: Optional[str] = None) -> Optional[dict]:
    """
    Retorna o registro completo de um ticker legado.

    Parameters
    ----------
    legacy_ticker : str
        Ticker legado a consultar (ex: "PETZ3").
    yaml_path : str | None
        Caminho alternativo para o YAML.

    Returns
    -------
    dict | None
        Registro completo do ticker legado, ou None se não encontrado.
    """
    key = str(legacy_ticker).strip().upper()
    for record in _load_yaml(yaml_path or str(_DEFAULT_YAML)):
        if str(record.get("legacy_ticker", "")).upper() == key:
            return record
    return None


def is_legacy_ticker(ticker: str, yaml_path: Optional[str] = None) -> bool:
    """
    Verifica se um ticker é legado (extinto por corporate action).

    Parameters
    ----------
    ticker : str
        Ticker a verificar (ex: "PETZ3").

    Returns
    -------
    bool
        True se o ticker está registrado como legado.

    Examples
    --------
    >>> is_legacy_ticker("PETZ3")
    True
    >>> is_legacy_ticker("AUAU3")
    False
    >>> is_legacy_ticker("VALE3")
    False
    """
    return get_alias_record(ticker, yaml_path) is not None


def resolve_ticker(ticker: str, yaml_path: Optional[str] = None) -> str:
    """
    Retorna o ticker ativo para um ticker (possivelmente legado).

    Se o ticker é legado, retorna o successor (current_ticker).
    Se o ticker já é ativo ou desconhecido, retorna o próprio ticker.

    Parameters
    ----------
    ticker : str
        Ticker a resolver (ex: "PETZ3" → "AUAU3"; "VALE3" → "VALE3").

    Returns
    -------
    str
        Ticker ativo (successor ou o próprio se não legado).

    Examples
    --------
    >>> resolve_ticker("PETZ3")
    'AUAU3'
    >>> resolve_ticker("VALE3")
    'VALE3'
    """
    record = get_alias_record(ticker, yaml_path)
    if record is None:
        return str(ticker).strip().upper()
    current = record.get("current_ticker")
    if current is None:
        # Ticker extinto sem successor (ex: delisted)
        log.warning(
            "resolve_ticker: '%s' é ticker legado sem successor — retornando legado",
            ticker,
        )
        return str(ticker).strip().upper()
    return str(current).strip().upper()


# ── Conjunto pré-computado de tickers legados ──────────────────────────────────

@lru_cache(maxsize=1)
def _build_legacy_set(yaml_path: str) -> frozenset[str]:
    records = _load_yaml(yaml_path)
    return frozenset(str(r.get("legacy_ticker", "")).upper() for r in records)


def legacy_tickers_set(yaml_path: Optional[str] = None) -> frozenset[str]:
    """Retorna frozenset com todos os tickers legados registrados."""
    return _build_legacy_set(yaml_path or str(_DEFAULT_YAML))


# Atalho de módulo (calculado na importação)
LEGACY_TICKERS: frozenset[str] = legacy_tickers_set()


# ── __all__ ────────────────────────────────────────────────────────────────────

__all__ = [
    "LEGACY_TICKERS",
    "is_legacy_ticker",
    "resolve_ticker",
    "get_corporate_actions",
    "get_alias_record",
    "legacy_tickers_set",
]
