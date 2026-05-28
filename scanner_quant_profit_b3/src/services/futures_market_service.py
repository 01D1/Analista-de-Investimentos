"""
Futures Market Service — Fonte canônica de futuros e índices
============================================================

Regras:
  - Lê RTD PROFIT.xlsx para dados de futuros e índices
  - Não calcula nada
  - Retorna status/timestamp/source/diagnostic

API pública:
  get_futures_live_payload()
  get_futures_summary_payload()
"""

from __future__ import annotations

import logging
from datetime import datetime
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

# Known future tokens
FUTURO_TOKENS = {
    "WDO", "DOL", "WIN", "IND", "DI1",
    "WDOFUT", "DOLFUT", "WINFUT", "DI1FUT",
    "WDOFW", "DOLFW", "WINFW",
}

INDICE_TOKERS = {
    "IBOV", "IBOVX100", "IBRA", "SMLL", "IFNC", "ICON", "IDIV", "IFIX",
    "IMOB", "UTIL", "MATER",
}


# ── Parse helpers ────────────────────────────────────────────────────────────

def _parse_br(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return None if (v != v) else v
    s = str(value).strip()
    if s in ("-", "", "nan", "None", "NaN"):
        return None
    s = s.replace("R$", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _parse_int(value) -> Optional[int]:
    v = _parse_br(value)
    return int(v) if v is not None else None


# ── Classify ────────────────────────────────────────────────────────────────

def _classify_instrument(ticker: str) -> str:
    t = str(ticker or "").strip().upper()
    if any(t.startswith(p) for p in ("WDO", "DOL", "WIN", "IND", "DI1")):
        return "FUTURO"
    if t in FUTURO_TOKENS:
        return "FUTURO"
    if t in INDICE_TOKERS:
        return "INDICE"
    if any(t.startswith(p) for p in ("IBOV", "SMLL", "IFIX", "IMOB", "UTIL", "MATER", "ICON", "IDIV")):
        return "INDICE"
    return "OUTRO"


# ── RTD reader ───────────────────────────────────────────────────────────────

def _read_all_rtd() -> pd.DataFrame:
    """Lê todas as abas do RTD, retorna DataFrame combinado."""
    if not RTD_PATH.exists():
        return pd.DataFrame()
    try:
        sheets = pd.read_excel(RTD_PATH, sheet_name=None, header=0)
        frames = []
        for name, df in sheets.items():
            df = df.copy()
            df.columns = [str(c).strip() for c in df.columns]
            df["_sheet"] = name
            if "Asset" in df.columns:
                df["_ticker"] = df["Asset"].astype(str).str.strip().str.upper()
            frames.append(df)
        if frames:
            return pd.concat(frames, ignore_index=True)
        return pd.DataFrame()
    except Exception as e:
        logger.warning(f"[futures_market] RTD read: {e}")
        return pd.DataFrame()


# ── Main functions ──────────────────────────────────────────────────────────

def get_futures_live_payload() -> dict[str, Any]:
    """
    Retorna todos os futuros e índices detectados no RTD PROFIT.xlsx.

    Returns:
        dict com: status, futures, indices, total, source, timestamp, diagnostic
    """
    df = _read_all_rtd()
    if df.empty:
        return {
            "status": "error",
            "futures": [],
            "indices": [],
            "total": 0,
            "error": "RTD PROFIT.xlsx não encontrado ou vazio",
            "source": "RTD PROFIT.xlsx",
            "timestamp": datetime.utcnow().isoformat(),
            "diagnostic": {
                "rtd_file": str(RTD_PATH),
                "rtd_exists": RTD_PATH.exists(),
                "data_type": "unavailable",
            },
        }

    futures_list: list[dict[str, Any]] = []
    indices_list: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        ticker = str(row.get("_ticker", "")).strip()
        if not ticker or ticker == "NAN":
            continue

        classe = _classify_instrument(ticker)
        if classe == "OUTRO":
            continue

        preco = _parse_br(row.get("Último"))
        variacao = _parse_br(row.get("Variação"))
        volume = _parse_br(row.get("Volume"))
        negocios = _parse_int(row.get("Negócios"))
        bid = _parse_br(row.get("Of. Compra"))
        ask = _parse_br(row.get("Of. Venda"))
        spread = (
            round(ask - bid, 4) if bid and ask and bid > 0 and ask > 0 else None
        )
        spread_pct = (
            round((ask - bid) / bid * 100, 4) if spread and bid and bid > 0 else None
        )
        vwap = _parse_br(row.get("VWAP"))
        nome = str(row.get("Nome do Ativo", ""))
        sheet = str(row.get("_sheet", ""))
        variacao_pts = _parse_br(row.get("Variação(pts)"))

        entry = {
            "ticker": ticker,
            "classe": classe,
            "nome": nome,
            "price": preco,
            "variation": variacao,
            "variation_pts": variacao_pts,
            "volume": volume,
            "trades": negocios,
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "spread_pct": spread_pct,
            "vwap": vwap,
            "aba_origem": sheet,
            "status": "AO_VIVO" if preco is not None else "SEM_PRECO",
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Identificar tipo de contrato
        if classe == "FUTURO":
            entry["contract_type"] = _derive_contract_type(ticker)
            futures_list.append(entry)
        else:
            indices_list.append(entry)

    total = len(futures_list) + len(indices_list)

    return {
        "status": "ok",
        "futures": futures_list,
        "indices": indices_list,
        "total": total,
        "futures_count": len(futures_list),
        "indices_count": len(indices_list),
        "source": "RTD PROFIT.xlsx",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_file": str(RTD_PATH),
            "rtd_exists": RTD_PATH.exists(),
            "sheets_read": list(df["_sheet"].unique()) if "_sheet" in df.columns else [],
            "data_type": "single_snapshot",
            "note": (
                "RTD PROFIT.xlsx fornece snapshot único por pregão. "
                "Futuros/DI/WDO/DOL precisam estar configurados no Profit RTD "
                "para aparecer aqui. Adicione contratos ao RTD se vazio."
            ),
            "limitations": [
                "Não há série temporal de futuros — snapshot único",
                "Futuros de renda fixa (DI) podem não estar no RTD padrão",
                "Contratos emolumentos (WIN/DOL) precisam de configuração especial",
            ],
        },
    }


def get_futures_summary_payload() -> dict[str, Any]:
    """
    Retorna resumo executivo de futuros e índices.
    Usado por: RadarAI, dashboard de macro.
    """
    live = get_futures_live_payload()

    if live.get("status") == "error":
        return live

    futures = live.get("futures", [])
    indices = live.get("indices", [])

    # Aggregations
    summary: dict[str, Any] = {
        "total": live.get("total", 0),
        "futures_count": len(futures),
        "indices_count": len(indices),
        "ao_vivo": sum(1 for f in futures + indices if f.get("status") == "AO_VIVO"),
        "by_ticker": {},
    }

    for item in futures + indices:
        ticker = item["ticker"]
        summary["by_ticker"][ticker] = {
            "classe": item.get("classe"),
            "price": item.get("price"),
            "variation": item.get("variation"),
            "variation_pts": item.get("variation_pts"),
            "volume": item.get("volume"),
            "trades": item.get("trades"),
            "status": item.get("status"),
        }

    # Special indices
    ibov = next((i for i in indices if i["ticker"] in ("IBOV", "IBOVX100")), None)
    if ibov:
        summary["ibov"] = ibov.get("price")

    return {
        **live,
        "summary": summary,
    }


def _derive_contract_type(ticker: str) -> str:
    """Deriva o tipo de contrato futuro a partir do ticker."""
    t = str(ticker or "").upper()
    if t.startswith("WDO") or "DOL" in t:
        return "DOL"  # Dólar
    if t.startswith("WIN"):
        return "WIN"  # Mini Índice
    if t.startswith("IND"):
        return "IND"  # Índice cheio
    if t.startswith("DI1") or t.startswith("DI"):
        return "DI"   # DI futuro
    return "OUTRO"


# ── Empty state helper ─────────────────────────────────────────────────────

def _empty_futures_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "futures": [],
        "indices": [],
        "total": 0,
        "futures_count": 0,
        "indices_count": 0,
        "source": "RTD PROFIT.xlsx",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_file": str(RTD_PATH),
            "rtd_exists": RTD_PATH.exists(),
            "data_type": "empty",
            "note": (
                "Nenhum futuro detectado no RTD atual. "
                "Adicione contratos (WDO, DOL, WIN, IND, DI1) ao Profit RTD "
                "para monitorá-los aqui."
            ),
        },
    }
