"""
src/valuation/tickers_config.py — Tickers YAML Configuration Loader (M016-S01)

Carrega e cacheia dados do tickers.yaml canônico para uso pelo SectorNormalizer.

Resolução de caminho (por precedência):
  1. Env var TICKERS_YAML_PATH (override explícito)
  2. config/tickers.yaml        — dentro do projeto scanner
  3. ../12_PYTHON/config/tickers.yaml — repositório Obsidian pai

Contratos:
  - Nunca lança exceção — retorna dict vazio se arquivo não encontrado
  - Cache em módulo evita I/O repetido; force_reload=True invalida cache
  - Apenas leitura — nunca escreve no arquivo

Proibido:
  - Calcular fair_value
  - Alterar banco
  - Criar mocks
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Cache de módulo ────────────────────────────────────────────────────────────

_TICKERS_CACHE: Optional[dict[str, dict]] = None
_TICKERS_YAML_PATH_USED: Optional[Path] = None


# ── Localização do arquivo ─────────────────────────────────────────────────────

def _find_tickers_yaml() -> Optional[Path]:
    """Localiza tickers.yaml canônico por ordem de precedência.

    Retorna Path se encontrado, None caso contrário.
    """
    # 1. Env var override
    env_path = os.environ.get("TICKERS_YAML_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        logger.warning("TICKERS_YAML_PATH=%s definido mas arquivo não encontrado", env_path)

    # 2. config/tickers.yaml dentro do projeto scanner
    scanner_root = Path(__file__).parent.parent.parent   # src/valuation/ -> src/ -> scanner_quant_profit_b3/
    candidates = [
        scanner_root / "config" / "tickers.yaml",
        scanner_root / "config" / "tickers.yml",
        # 3. Repositório Obsidian pai: ../12_PYTHON/config/tickers.yaml
        scanner_root.parent / "12_PYTHON" / "config" / "tickers.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p

    return None


# ── Loader ─────────────────────────────────────────────────────────────────────

def load_tickers_config(force_reload: bool = False) -> dict[str, dict]:
    """Carrega tickers.yaml e retorna dict: TICKER_UPPER → config dict.

    Parâmetros
    ----------
    force_reload: bool
        Se True, invalida o cache e relê o arquivo.

    Retorno
    -------
    dict[str, dict]
        Chaves: ticker em UPPER (ex: "PETR4"). Valores: dict com type, sector, active, priority…
        Retorna {} se arquivo não encontrado ou com erro de parse.
    """
    global _TICKERS_CACHE, _TICKERS_YAML_PATH_USED

    if _TICKERS_CACHE is not None and not force_reload:
        return _TICKERS_CACHE

    path = _find_tickers_yaml()
    if path is None:
        logger.warning(
            "tickers.yaml não encontrado. SectorNormalizer usará apenas mapeamento estático. "
            "Defina TICKERS_YAML_PATH ou coloque o arquivo em config/tickers.yaml"
        )
        _TICKERS_CACHE = {}
        return {}

    try:
        import yaml  # lazy import — yaml é dependência opcional para este módulo
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            logger.error("tickers.yaml: formato inesperado (esperado dict, got %s)", type(raw))
            _TICKERS_CACHE = {}
            return {}

        tickers_list = raw.get("tickers", [])
        if not isinstance(tickers_list, list):
            logger.error("tickers.yaml: campo 'tickers' deve ser lista")
            _TICKERS_CACHE = {}
            return {}

        result: dict[str, dict] = {}
        for entry in tickers_list:
            if not isinstance(entry, dict):
                continue
            ticker_key = str(entry.get("ticker", "")).strip().upper()
            if ticker_key:
                result[ticker_key] = entry

        _TICKERS_CACHE = result
        _TICKERS_YAML_PATH_USED = path
        logger.debug("tickers.yaml carregado: %d tickers de %s", len(result), path)
        return result

    except ImportError:
        logger.error("PyYAML não instalado. Instale com: pip install pyyaml")
        _TICKERS_CACHE = {}
        return {}
    except Exception as exc:
        logger.error("Erro ao carregar tickers.yaml de %s: %s", path, exc)
        _TICKERS_CACHE = {}
        return {}


def get_ticker_config(ticker: str) -> Optional[dict]:
    """Retorna config dict de um ticker, ou None se não encontrado.

    Parâmetros
    ----------
    ticker: str
        Código do ativo (ex: "PETR4"). Case-insensitive.

    Retorno
    -------
    dict | None
        Dict com campos: ticker, name, type, sector, active, priority.
        None se ticker não está no tickers.yaml.
    """
    cfg = load_tickers_config()
    return cfg.get(str(ticker).strip().upper())


def get_ticker_type(ticker: str) -> Optional[str]:
    """Retorna o campo 'type' de um ticker do tickers.yaml.

    Retorna None se ticker não encontrado ou campo ausente.
    Ex: get_ticker_type("BBAS3") → "bank"
        get_ticker_type("PETR4") → "oil_gas"
    """
    entry = get_ticker_config(ticker)
    if entry is None:
        return None
    return entry.get("type")


def get_ticker_yaml_path() -> Optional[Path]:
    """Retorna o caminho do tickers.yaml carregado, ou None se não carregado."""
    if _TICKERS_YAML_PATH_USED is None:
        load_tickers_config()  # trigger load
    return _TICKERS_YAML_PATH_USED


def invalidate_cache() -> None:
    """Invalida o cache forçando reload na próxima chamada. Útil em testes."""
    global _TICKERS_CACHE, _TICKERS_YAML_PATH_USED
    _TICKERS_CACHE = None
    _TICKERS_YAML_PATH_USED = None


__all__ = [
    "load_tickers_config",
    "get_ticker_config",
    "get_ticker_type",
    "get_ticker_yaml_path",
    "invalidate_cache",
]
