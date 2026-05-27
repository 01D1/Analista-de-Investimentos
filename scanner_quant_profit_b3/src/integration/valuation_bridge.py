"""
Valuation Bridge — lê os outputs do pipeline_banco_completo.

Estratégia: encontra o Excel mais recente de cada ticker em
`outputs/Valuation_<TICKER>_*.xlsx` e extrai preço-alvo e upside.
Somente leitura — nunca altera o projeto de origem.

Performance:
  - _AVAILABLE_TICKERS_CACHE: um único glob por outputs_dir para saber quais tickers
    têm Excel antes de abrir qualquer arquivo.
  - _VALUATION_CACHE: cache em memória dos resultados por (outputs_dir, ticker) para
    não reler o Excel a cada render do Streamlit.
  - _read_excel_valuation: parseia no máximo MAX_SHEETS abas por arquivo.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Cache em memória (escopo do processo Python — persiste entre renders)
# ---------------------------------------------------------------------------

# { str(outputs_dir) → set[ticker] }
_AVAILABLE_TICKERS_CACHE: dict[str, set[str]] = {}

# { (str(outputs_dir), ticker) → dict }
_VALUATION_CACHE: dict[tuple[str, str], dict] = {}

# Máximo de abas a parsear por arquivo (evita bloquear em Excels grandes)
MAX_SHEETS = 3
# Máximo de linhas a ler por aba (evita bloquear em planilhas com histórico longo)
MAX_ROWS = 200


# ---------------------------------------------------------------------------
# Localização do Excel
# ---------------------------------------------------------------------------

def _scan_available_tickers(outputs_dir: Path) -> set[str]:
    """Faz UM glob para mapear todos os tickers disponíveis no diretório.

    Resultado fica em _AVAILABLE_TICKERS_CACHE para não repetir I/O.
    """
    key = str(outputs_dir)
    if key in _AVAILABLE_TICKERS_CACHE:
        return _AVAILABLE_TICKERS_CACHE[key]

    available: set[str] = set()
    try:
        for f in outputs_dir.glob("Valuation_*.xlsx"):
            m = re.match(r"Valuation_([A-Z0-9]+)_", f.name)
            if m:
                available.add(m.group(1))
    except Exception:
        pass
    _AVAILABLE_TICKERS_CACHE[key] = available
    return available


def _find_latest_excel(outputs_dir: Path, ticker: str) -> Optional[Path]:
    """Retorna o Excel mais recente para o ticker, ou None se não encontrar."""
    pattern = f"Valuation_{ticker}_*.xlsx"
    candidates = sorted(outputs_dir.glob(pattern), reverse=True)
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Extração de valores do Excel
# ---------------------------------------------------------------------------

_PRICE_LABELS = [
    "preco justo", "preco teto", "preço justo", "preço teto",
    "p.alvo", "p. alvo", "target", "valor justo", "dcf",
    "preco_alvo", "preço_alvo",
]

_UPSIDE_LABELS = [
    "upside", "potencial", "margem de segurança", "margem segurança",
    "retorno esperado",
]


def _search_cells(df: pd.DataFrame) -> dict:
    """
    Percorre o DataFrame (lido sem cabeçalho) procurando células com rótulos
    de preço-alvo e upside. Retorna dict com os valores encontrados.
    Para quando encontra ambos os valores.
    """
    result: dict = {}
    str_df = df.astype(str).apply(lambda col: col.str.lower().str.strip())

    for i, row in str_df.iterrows():
        for j, cell in row.items():
            # Preço-alvo
            if any(label in cell for label in _PRICE_LABELS) and "preco_alvo" not in result:
                for offset in [1, 2]:
                    try:
                        val = pd.to_numeric(df.iloc[i, j + offset], errors="coerce")
                        if pd.notna(val) and 0 < val < 10_000:
                            result["preco_alvo"] = round(float(val), 2)
                            break
                    except (IndexError, TypeError):
                        pass

            # Upside
            if any(label in cell for label in _UPSIDE_LABELS) and "upside_pct" not in result:
                for offset in [1, 2]:
                    try:
                        val = pd.to_numeric(df.iloc[i, j + offset], errors="coerce")
                        if pd.notna(val):
                            if abs(val) < 5:
                                val = val * 100
                            result["upside_pct"] = round(float(val), 1)
                            break
                    except (IndexError, TypeError):
                        pass

        # Saída antecipada quando ambos já foram encontrados
        if "preco_alvo" in result and "upside_pct" in result:
            return result

    return result


def _read_excel_valuation(path: Path, ticker: str) -> dict:
    """Lê no máximo MAX_SHEETS abas do Excel e agrega os valores encontrados.

    Limita abas para não bloquear em arquivos com muitas planilhas.
    """
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
    except Exception:
        return {}

    aggregated: dict = {}
    sheets_to_read = xl.sheet_names[:MAX_SHEETS]

    for sheet in sheets_to_read:
        try:
            df = xl.parse(sheet, header=None)
            found = _search_cells(df)
            aggregated.update(found)
        except Exception:
            continue
        # Saída antecipada quando ambos os valores já foram encontrados
        if "preco_alvo" in aggregated and "upside_pct" in aggregated:
            break

    aggregated["fonte"] = path.name
    aggregated["ticker"] = ticker
    aggregated["data_valuation"] = _extract_date_from_filename(path.name)
    return aggregated


def _extract_date_from_filename(name: str) -> str:
    """Extrai data do padrão Valuation_TICKER_Nome_YYYYMMDD.xlsx."""
    m = re.search(r"(\d{8})", name)
    if m:
        d = m.group(1)
        try:
            return datetime.strptime(d, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

def list_available_tickers(outputs_dir: str | Path) -> set[str]:
    """Retorna o conjunto de tickers com Excel disponível (sem abrir arquivos).

    Usa _AVAILABLE_TICKERS_CACHE — O(1) após o primeiro acesso.
    """
    outputs_dir = Path(outputs_dir)
    if not outputs_dir.exists():
        return set()
    return _scan_available_tickers(outputs_dir)


def get_valuation(ticker: str, outputs_dir: str | Path) -> dict:
    """
    Retorna dict com preço-alvo e upside para o ticker, ou {} se não encontrado.

    Cache em memória (_VALUATION_CACHE) — relê o Excel apenas uma vez por sessão.
    Verifica disponibilidade via _scan_available_tickers antes de abrir qualquer arquivo.

    Args:
        ticker:      código do ativo (ex: "BBDC4")
        outputs_dir: caminho para a pasta outputs/ do pipeline_banco_completo
    """
    outputs_dir = Path(outputs_dir)
    if not outputs_dir.exists():
        return {}

    # 1. Verificar cache em memória
    cache_key = (str(outputs_dir), str(ticker).upper())
    if cache_key in _VALUATION_CACHE:
        return _VALUATION_CACHE[cache_key]

    # 2. Verificar se ticker tem Excel sem abrir arquivo (O(1) após primeiro glob)
    available = _scan_available_tickers(outputs_dir)
    if ticker.upper() not in available:
        _VALUATION_CACHE[cache_key] = {}
        return {}

    # 3. Encontrar e ler o Excel mais recente
    excel_path = _find_latest_excel(outputs_dir, ticker)
    if excel_path is None:
        _VALUATION_CACHE[cache_key] = {}
        return {}

    result = _read_excel_valuation(excel_path, ticker)
    _VALUATION_CACHE[cache_key] = result
    return result


def get_valuations_batch(tickers: list[str], outputs_dir: str | Path) -> dict[str, dict]:
    """Retorna dict {ticker: valuation} para uma lista de tickers.

    Usa list_available_tickers() para um único glob antes de abrir qualquer arquivo.
    """
    outputs_dir = Path(outputs_dir)
    available = list_available_tickers(outputs_dir)

    result: dict[str, dict] = {}
    for t in tickers:
        if t.upper() in available:
            result[t] = get_valuation(t, outputs_dir)
        else:
            result[t] = {}
    return result


def list_valid_valuations(outputs_dir: str | Path | None = None) -> list[str]:
    """Lista tickers com valuation válido (preco_alvo presente).

    Usado por radar_quant.py para cobertura de valuation.
    """
    if outputs_dir is None:
        try:
            from src.utils import project_path
            outputs_dir = project_path("12_PYTHON/pipeline banco completo/outputs")
        except Exception:
            return []

    outputs_dir = Path(outputs_dir)
    if not outputs_dir.exists():
        return []

    available = list_available_tickers(outputs_dir)
    valid = []
    for t in sorted(available):
        vd = get_valuation(t, outputs_dir)
        if vd.get("preco_alvo"):
            valid.append(t)
    return valid
