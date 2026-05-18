"""Normalização de cadeias de opções para o modelo institucional."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

from src.options.options_metrics import calculate_days_to_maturity, calculate_spread_metrics
from src.options.options_model import OPTION_COLUMNS, empty_options_frame


CALL_MONTH_CODES = set("ABCDEFGHIJKL")
PUT_MONTH_CODES = set("MNOPQRSTUVWX")


def infer_option_type(option_ticker: str, metadata: dict | None = None) -> str:
    explicit = str((metadata or {}).get("option_type") or (metadata or {}).get("type") or "").upper()
    if explicit in {"CALL", "PUT"}:
        return explicit
    ticker = str(option_ticker or "").upper().strip()
    if len(ticker) >= 5:
        code = ticker[4]
        if code in CALL_MONTH_CODES:
            return "CALL"
        if code in PUT_MONTH_CODES:
            return "PUT"
    return "UNKNOWN"


def _first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def normalize_options_chain(raw_df: pd.DataFrame, reference_date: Any | None = None) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return empty_options_frame()
    raw = raw_df.copy()
    mapping = {
        "option_ticker": ["option_ticker", "ticker", "symbol"],
        "underlying": ["underlying", "ativo_base_estimado", "asset", "underlying_asset"],
        "option_type": ["option_type", "type", "tipo"],
        "strike": ["strike", "option_exercise_price", "preco_exercicio"],
        "maturity_date": ["maturity_date", "expiration_date", "option_maturity", "vencimento"],
        "last_price": ["last_price", "close", "last", "ultimo"],
        "bid": ["bid", "best_bid"],
        "ask": ["ask", "best_ask"],
        "volume": ["volume"],
        "trades": ["trades", "negocios"],
        "open_interest": ["open_interest", "openinterest"],
        "underlying_price": ["underlying_price", "stock_price", "spot"],
    }
    out = pd.DataFrame()
    for target, candidates in mapping.items():
        src = _first_existing(raw, candidates)
        out[target] = raw[src] if src else pd.NA
    out["option_ticker"] = out["option_ticker"].astype(str).str.upper().str.strip()
    out["underlying"] = out["underlying"].astype(str).str.upper().str.strip().replace({"": pd.NA, "NAN": pd.NA, "<NA>": pd.NA})
    out["maturity_date"] = pd.to_datetime(out["maturity_date"], errors="coerce").dt.date.astype("string")
    for col in ["strike", "last_price", "bid", "ask", "volume", "trades", "open_interest", "underlying_price"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["option_type"] = [
        typ if str(typ).upper() in {"CALL", "PUT"} else infer_option_type(ticker, {"option_type": typ})
        for ticker, typ in zip(out["option_ticker"], out["option_type"])
    ]
    ref = reference_date
    if ref is None:
        src = _first_existing(raw, ["trade_date", "date"])
        ref = raw[src].iloc[0] if src and not raw.empty else date.today()
    out["days_to_maturity"] = out["maturity_date"].apply(lambda x: calculate_days_to_maturity(x, ref))
    spreads = [calculate_spread_metrics(b, a, p) for b, a, p in zip(out["bid"], out["ask"], out["last_price"])]
    out["spread"] = [s[0] for s in spreads]
    out["spread_pct"] = [s[1] for s in spreads]
    out["financial_volume"] = out["volume"].fillna(0) * out["last_price"].fillna(0)
    for col in OPTION_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out["metadata_json"] = [json.dumps({}, ensure_ascii=False)] * len(out)
    return out[OPTION_COLUMNS]


def validate_options_chain(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df is None or df.empty:
        return empty_options_frame(), pd.DataFrame([{"issue": "EMPTY", "count": 0}])
    work = df.copy()
    issues = []
    masks = {
        "STRIKE_AUSENTE": pd.to_numeric(work.get("strike"), errors="coerce").isna(),
        "VENCIMENTO_AUSENTE": pd.to_datetime(work.get("maturity_date"), errors="coerce").isna(),
        "PRECO_AUSENTE": pd.to_numeric(work.get("last_price"), errors="coerce").isna(),
        "VOLUME_AUSENTE": pd.to_numeric(work.get("volume"), errors="coerce").isna(),
        "BID_MAIOR_ASK": pd.to_numeric(work.get("bid"), errors="coerce") > pd.to_numeric(work.get("ask"), errors="coerce"),
        "VENCIMENTO_PASSADO": pd.to_numeric(work.get("days_to_maturity"), errors="coerce") < 0,
        "UNDERLYING_AUSENTE": work.get("underlying", pd.Series(index=work.index)).isna(),
    }
    valid = pd.Series(True, index=work.index)
    for issue, mask in masks.items():
        mask = mask.fillna(False)
        issues.append({"issue": issue, "count": int(mask.sum())})
        valid &= ~mask
    return work[valid].reset_index(drop=True), pd.DataFrame(issues)
