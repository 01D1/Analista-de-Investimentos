"""
Market History Service — Fonte canônica de histórico de ações
==============================================================

Regras:
  - Lê RTD PROFIT.xlsx como fonte histórica primária (preço, OHLCV, indicadores)
  - Lê options CSV como fonte de contexto de opções
  - Não calcula nada — apenas agrega e expõe dados existentes
  - Não escreve no banco
  - Retorna sempre status/timestamp/source/diagnostic

API pública:
  get_asset_history_payload(ticker, period)
  get_multi_asset_history_summary(tickers)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

def _scanner_root() -> Path:
    p = Path(__file__).resolve().parents[2]
    if (p / "src").is_dir():
        return p
    return Path.cwd()


RTD_PATH = _scanner_root() / "data" / "realtime" / "RTD PROFIT.xlsx"

# Períodos disponíveis (períodos de dias úteis)
_PERIOD_DAYS = {
    "1w":  5,
    "2w":  10,
    "1m":  21,
    "3m":  63,
    "6m":  126,
    "1y":  252,
    "ytd": 0,    # calculado dinamicamente
}


# ── RTD reader ───────────────────────────────────────────────────────────────

def _read_rtd_actions() -> pd.DataFrame:
    """Lê aba Ações do RTD PROFIT.xlsx, retorna DataFrame."""
    if not RTD_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(RTD_PATH, sheet_name="Ações", header=0)
        df.columns = [str(c).strip() for c in df.columns]
        # Normalizar ticker
        if "Asset" in df.columns:
            df["_ticker"] = df["Asset"].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        logger.warning(f"[market_history] RTD Ações: {e}")
        return pd.DataFrame()


# ── Parse helpers ────────────────────────────────────────────────────────────

def _parse_br(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return None if (v != v) else v  # nan guard
    s = str(value).strip()
    if s in ("-", "", "nan", "None", "NaN"):
        return None
    s = s.replace("R$", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _is_action(ticker: str) -> bool:
    """Detecta se ticker é ação B3 (termina em 3/4/5/6/11)."""
    t = str(ticker or "").strip()
    return len(t) >= 4 and (t[-2:] in ("11",) or t[-1:] in ("3", "4", "5", "6"))


def _classify_rtd_row(row: dict) -> str:
    """Classifica uma linha do RTD como ação/índice/outro."""
    ticker = str(row.get("Asset", row.get("_ticker", ""))).strip()
    if _is_action(ticker):
        return "ACAO"
    if ticker in ("IBOV", "IBOVX100", "IBRA", "SMLL", "IFNC", "ICON", "IDIV", "IFIX"):
        return "INDICE"
    return "OUTRO"


# ── Main functions ───────────────────────────────────────────────────────────

def get_asset_history_payload(
    ticker: str,
    period: str = "1y",
) -> dict[str, Any]:
    """
    Retorna histórico de preço + indicadores para um ticker de ação.

    Fonte: RTD PROFIT.xlsx (aba Ações), que fornece snapshot de OHLCV + indicadores.

    Args:
        ticker: ticker B3, ex: "PETR4", "VALE3", "WEGE3"
        period: período desejado (1w/1m/3m/6m/1y/ytd). Se RTD é apenas snapshot
                atual, retorna dados do momento disponível com indicador de período.

    Returns:
        dict com: ticker, period, ohlcv, summary, source, timestamp, diagnostic
    """
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return _empty_payload("ticker vazio")

    df_rtd = _read_rtd_actions()
    if df_rtd.empty:
        return _empty_payload(
            "RTD PROFIT.xlsx não encontrado ou vazio",
            ticker=ticker,
            period=period,
        )

    # Normalizar: tentar todas as variações do ticker
    candidates = {ticker}
    if len(ticker) == 5 and ticker[-1] in ("3", "4", "5", "6", "11"):
        # PETR4 → PETR, VALE3 → VALE
        candidates.add(ticker[:-1])
        candidates.add(ticker[:-1] + "3")
        candidates.add(ticker[:-1] + "4")

    row = None
    matched_ticker = None
    for t in candidates:
        matches = df_rtd[df_rtd["_ticker"].str.upper() == t.upper()]
        if not matches.empty:
            row = matches.iloc[0].to_dict()
            matched_ticker = t
            break

    if row is None:
        # Tentar busca parcial (prefixo)
        partial = df_rtd[df_rtd["_ticker"].str.startswith(ticker[:4].upper())]
        if not partial.empty:
            row = partial.iloc[0].to_dict()
            matched_ticker = row.get("_ticker", ticker)
        else:
            return _empty_payload(
                f"ticker {ticker} não encontrado no RTD",
                ticker=ticker,
                period=period,
            )

    # Extrair valores
    preco = _parse_br(row.get("Último"))
    variacao = _parse_br(row.get("Variação"))
    volume = _parse_br(row.get("Volume"))
    negocios = _parse_br(row.get("Negócios"))
    vwap = _parse_br(row.get("VWAP"))
    rsi = _parse_br(row.get("IFR (RSI)"))
    macd = _parse_br(row.get("MACD Histograma"))
    adx = _parse_br(row.get("ADX"))
    boll_b = _parse_br(row.get("Bollinger b%"))
    hilo = _parse_br(row.get("HiLo Activator"))
    nome = str(row.get("Nome do Ativo", ""))
    abertura = _parse_br(row.get("Abertura"))
    maxima = _parse_br(row.get("Máximo"))
    minima = _parse_br(row.get("Mínimo"))
    fechamento_anterior = _parse_br(row.get("Fechamento Anterior"))
    ajuste = _parse_br(row.get("Ajuste"))
    volatilidade = _parse_br(row.get("Volatilidade Histórica"))
    volatilidade_media = _parse_br(row.get("Volatilidade Histórica Média"))

    # Meta: variações por período
    metas = {}
    for label, col in [
        ("semana", "Semana"),
        ("mes", "Mês"),
        ("3meses", "3 meses"),
        ("6meses", "6 meses"),
        ("12meses", "12 meses"),
        ("ano", "Ano"),
        ("trimestre", "Trimestre"),
        ("semestre", "Semestre"),
    ]:
        if col in row and row[col] is not None:
            metas[label] = _parse_br(row.get(col))

    # Classificação
    classe = _classify_rtd_row(row)

    # OHLCV snapshot (RTD é ponto único, não série temporal)
    ohlcv = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": preco,
        "close_prev": fechamento_anterior,
        "adjustment": ajuste,
        "volume": volume,
        "trades": negocios,
        "vwap": vwap,
    }

    # Para o RTD (snapshot único), não temos série temporal.
    # Retornamos "period_available" = "single_snapshot" e sinalizamos no diagnostic.
    period_available = "single_snapshot"

    # Summary — indicadores calculados a partir dos valores disponíveis
    summary: dict[str, Any] = {
        "last_close": preco,
        "variacao_dia": variacao,
        "nome": nome,
        "classe": classe,
        "vwap": vwap,
        "rsi": rsi,
        "macd": macd,
        "adx": adx,
        "bollinger_b": boll_b,
        "hilo": hilo,
        "volatilidade_hist": volatilidade,
        "volatilidade_hist_media": volatilidade_media,
        "meta_retornos": metas,
        # High/low dos últimos períodos — aproximado do RTD
        "high_periodo_52w": None,  # não disponível no snapshot RTD
        "low_periodo_52w": None,
        "distance_from_high_52w": None,
        "distance_from_low_52w": None,
        # Retornos por período
        "return_semana": metas.get("semana"),
        "return_mes": metas.get("mes"),
        "return_3m": metas.get("3meses"),
        "return_6m": metas.get("6meses"),
        "return_12m": metas.get("12meses"),
        "return_ytd": metas.get("ano"),
        "return_trimestre": metas.get("trimestre"),
        "return_semestre": metas.get("semestre"),
        # Vol/negócios
        "volume_media": volume,   # único valor disponível
        "trades_media": negocios,
        # 52w
        "avg_volume_21d": None,
        "avg_trades_21d": None,
        "volatility_21d": None,
        "volatility_63d": None,
    }

    return {
        "status": "ok",
        "ticker": ticker,
        "ticker_matched": matched_ticker,
        "period": period,
        "period_available": period_available,
        "start_date": None,
        "end_date": None,
        "ohlcv": ohlcv,
        "indicators": {
            "rsi": rsi,
            "macd": macd,
            "adx": adx,
            "bollinger_b": boll_b,
            "hilo": hilo,
            "volatilidade_hist": volatilidade,
        },
        "summary": summary,
        "source": "RTD PROFIT.xlsx / Ações",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_file": str(RTD_PATH),
            "rtd_exists": RTD_PATH.exists(),
            "matched_from_rtd": matched_ticker is not None,
            "data_type": "single_snapshot",
            "note": (
                "RTD PROFIT.xlsx fornece snapshot único por ativo. "
                "Para série temporal OHLCV, executar M015 (COTAHIST download). "
                "Dados retornados são do último pregão disponível no RTD."
            ),
            "limitations": [
                "Não há série temporal — apenas ponto único",
                "High/Low 52w não disponível no snapshot",
                "Vol média 21d não disponível",
                "Para histórico completo, rodar COTAHIST daily ingestion",
            ],
            "fields_available": list(row.keys()),
        },
    }


def get_multi_asset_history_summary(
    tickers: list[str],
) -> dict[str, Any]:
    """
    Retorna resumo histórico para múltiplos tickers.
    Usado por: Watchlist, RadarAI, cards de ações no frontend.

    Args:
        tickers: lista de tickers, ex: ["PETR4", "VALE3", "WEGE3"]

    Returns:
        dict com: status, tickers (lista de resumos), total, missing, timestamp, diagnostic
    """
    if not tickers:
        return {
            "status": "ok",
            "tickers": [],
            "total": 0,
            "missing": [],
            "timestamp": datetime.utcnow().isoformat(),
            "source": "RTD PROFIT.xlsx / Ações",
            "diagnostic": {"note": "nenhum ticker solicitado"},
        }

    results: list[dict[str, Any]] = []
    missing: list[str] = []

    for ticker in tickers:
        ticker = str(ticker).strip().upper()
        payload = get_asset_history_payload(ticker, period="snapshot")
        if payload["status"] == "ok":
            results.append({
                "ticker": payload["ticker"],
                "ticker_matched": payload.get("ticker_matched"),
                "last_close": payload["summary"].get("last_close"),
                "variacao_dia": payload["summary"].get("variacao_dia"),
                "classe": payload["summary"].get("classe"),
                "rsi": payload["indicators"].get("rsi"),
                "adx": payload["indicators"].get("adx"),
                "return_semana": payload["summary"].get("return_semana"),
                "return_mes": payload["summary"].get("return_mes"),
                "return_3m": payload["summary"].get("return_3m"),
                "volatilidade": payload["indicators"].get("volatilidade_hist"),
                "nome": payload["summary"].get("nome"),
            })
        else:
            missing.append(ticker)

    return {
        "status": "ok" if len(results) > 0 else "partial",
        "total": len(results),
        "missing": missing,
        "tickers": results,
        "source": "RTD PROFIT.xlsx / Ações",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_file": str(RTD_PATH),
            "found": len(results),
            "missing_count": len(missing),
            "data_type": "single_snapshot",
            "note": "RTD fornece apenas ponto único. Para histórico completo, rodar COTAHIST ingestion.",
        },
    }


def get_all_actions_from_rtd() -> dict[str, Any]:
    """
    Retorna TODAS as ações disponíveis no RTD PROFIT.xlsx.
    Usado por: RadarAI, Trading Desk, Watchlist cards.
    """
    df = _read_rtd_actions()
    if df.empty:
        return {
            "status": "ok",
            "actions": [],
            "total": 0,
            "source": "RTD PROFIT.xlsx / Ações",
            "timestamp": datetime.utcnow().isoformat(),
            "diagnostic": {"note": "RTD vazio ou não encontrado"},
        }

    acoes = df[df["_ticker"].apply(_is_action)].copy()
    acoes["_ticker_upper"] = acoes["_ticker"].str.upper()

    results = []
    for _, row in acoes.iterrows():
        ticker = str(row.get("_ticker", "")).strip().upper()
        if not ticker or ticker == "NAN":
            continue

        results.append({
            "ticker": ticker,
            "nome": str(row.get("Nome do Ativo", "")),
            "preco": _parse_br(row.get("Último")),
            "variacao": _parse_br(row.get("Variação")),
            "variacao_pts": _parse_br(row.get("Variação(pts)")),
            "abertura": _parse_br(row.get("Abertura")),
            "maxima": _parse_br(row.get("Máximo")),
            "minima": _parse_br(row.get("Mínimo")),
            "fechamento_anterior": _parse_br(row.get("Fechamento Anterior")),
            "volume": _parse_br(row.get("Volume")),
            "negocios": _parse_br(row.get("Negócios")),
            "vwap": _parse_br(row.get("VWAP")),
            "bid": _parse_br(row.get("Of. Compra")),
            "ask": _parse_br(row.get("Of. Venda")),
            "rsi": _parse_br(row.get("IFR (RSI)")),
            "macd": _parse_br(row.get("MACD Histograma")),
            "adx": _parse_br(row.get("ADX")),
            "bollinger_b": _parse_br(row.get("Bollinger b%")),
            "hilo": _parse_br(row.get("HiLo Activator")),
            "volatilidade": _parse_br(row.get("Volatilidade Histórica")),
            "meta_semana": _parse_br(row.get("Semana")),
            "meta_mes": _parse_br(row.get("Mês")),
            "meta_3m": _parse_br(row.get("3 meses")),
            "meta_6m": _parse_br(row.get("6 meses")),
            "meta_12m": _parse_br(row.get("12 meses")),
            "meta_ano": _parse_br(row.get("Ano")),
            "timestamp": datetime.utcnow().isoformat(),
        })

    return {
        "status": "ok",
        "total": len(results),
        "actions": results,
        "source": "RTD PROFIT.xlsx / Ações",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_file": str(RTD_PATH),
            "rtd_exists": RTD_PATH.exists(),
            "rows_total": len(acoes),
            "data_type": "single_snapshot",
            "columns_available": list(df.columns),
        },
    }


def _empty_payload(reason: str, ticker: str = "", period: str = "") -> dict[str, Any]:
    return {
        "status": "error",
        "ticker": ticker,
        "period": period,
        "error": reason,
        "ohlcv": [],
        "summary": {},
        "source": "RTD PROFIT.xlsx",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "reason": reason,
            "rtd_file": str(RTD_PATH),
            "data_type": "unavailable",
        },
    }