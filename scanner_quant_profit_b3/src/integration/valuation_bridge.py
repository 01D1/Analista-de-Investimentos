"""
Valuation Bridge — lê os outputs do pipeline_banco_completo.

Estratégia: encontra o Excel mais recente de cada ticker em
`outputs/Valuation_<TICKER>_*.xlsx` e extrai preço-alvo e upside.
Somente leitura — nunca altera o projeto de origem.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Localização do Excel
# ---------------------------------------------------------------------------

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
    """
    result: dict = {}
    # Converte tudo para string lower para busca
    str_df = df.astype(str).apply(lambda col: col.str.lower().str.strip())

    for i, row in str_df.iterrows():
        for j, cell in row.items():
            # Preço-alvo
            if any(label in cell for label in _PRICE_LABELS) and "preco_alvo" not in result:
                # Tenta ler a célula à direita ou abaixo
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
                            # Pode estar em decimal (0.35) ou percentual (35.0)
                            if abs(val) < 5:
                                val = val * 100
                            result["upside_pct"] = round(float(val), 1)
                            break
                    except (IndexError, TypeError):
                        pass

    return result


def _read_excel_valuation(path: Path, ticker: str) -> dict:
    """Lê todas as abas do Excel e agrega os valores encontrados."""
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
    except Exception:
        return {}

    aggregated: dict = {}
    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet, header=None)
            found = _search_cells(df)
            aggregated.update(found)
        except Exception:
            continue

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

def get_valuation(ticker: str, outputs_dir: str | Path) -> dict:
    """
    Retorna dict com preço-alvo e upside para o ticker, ou {} se não encontrado.

    Args:
        ticker:      código do ativo (ex: "BBDC4")
        outputs_dir: caminho para a pasta outputs/ do pipeline_banco_completo
    """
    outputs_dir = Path(outputs_dir)
    if not outputs_dir.exists():
        return {}

    excel_path = _find_latest_excel(outputs_dir, ticker)
    if excel_path is None:
        return {}

    return _read_excel_valuation(excel_path, ticker)


def get_valuations_batch(tickers: list[str], outputs_dir: str | Path) -> dict[str, dict]:
    """Retorna dict {ticker: valuation} para uma lista de tickers."""
    return {t: get_valuation(t, outputs_dir) for t in tickers}
