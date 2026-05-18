"""Estruturas básicas de opções para estudo quantitativo."""
from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pandas as pd


CONTRACT_SIZE = 100


def _price(row: pd.Series) -> float:
    return float(row.get("last_price") or 0)


def _leg(row: pd.Series, direction: str, quantity: int = 1) -> dict[str, Any]:
    return {
        "option_ticker": row.get("option_ticker"),
        "option_type": row.get("option_type"),
        "direction": direction,
        "strike": float(row.get("strike") or 0),
        "price": _price(row),
        "quantity": quantity,
        "liquidity_score": float(row.get("liquidity_score") or 0),
    }


def _structure(structure_type: str, underlying: str, maturity_date: str, legs: list[dict[str, Any]], **extra) -> dict[str, Any]:
    liquidity = float(np.mean([l.get("liquidity_score", 0) for l in legs])) if legs else 0.0
    out = {
        "structure_id": f"{structure_type}_{underlying}_{maturity_date}_{abs(hash(json.dumps(legs, sort_keys=True))) % 10_000_000}",
        "structure_type": structure_type,
        "underlying": underlying,
        "maturity_date": maturity_date,
        "legs_json": json.dumps(legs, ensure_ascii=False),
        "net_debit": 0.0,
        "net_credit": 0.0,
        "max_profit": math.nan,
        "max_loss": math.nan,
        "breakeven": math.nan,
        "payoff_ratio": math.nan,
        "probability_hint": "",
        "liquidity_score": liquidity,
        "risk_score": 0.0,
        "suitability_notes": "",
        "metadata_json": json.dumps({}, ensure_ascii=False),
    }
    out.update(extra)
    out["payoff_ratio"] = calculate_risk_reward(out)
    return out


def build_long_call(option_row: pd.Series) -> dict[str, Any]:
    leg = _leg(option_row, "BUY")
    price = leg["price"]
    strike = leg["strike"]
    return _structure(
        "LONG_CALL",
        str(option_row.get("underlying")),
        str(option_row.get("maturity_date")),
        [leg],
        net_debit=price * CONTRACT_SIZE,
        max_profit=math.inf,
        max_loss=price * CONTRACT_SIZE,
        breakeven=strike + price,
        risk_score=float(option_row.get("risk_score") or 0),
        suitability_notes="Estrutura direcional de alta para estudo; risco limitado ao prêmio.",
    )


def build_long_put(option_row: pd.Series) -> dict[str, Any]:
    leg = _leg(option_row, "BUY")
    price = leg["price"]
    strike = leg["strike"]
    return _structure(
        "LONG_PUT",
        str(option_row.get("underlying")),
        str(option_row.get("maturity_date")),
        [leg],
        net_debit=price * CONTRACT_SIZE,
        max_profit=max(strike - price, 0) * CONTRACT_SIZE,
        max_loss=price * CONTRACT_SIZE,
        breakeven=strike - price,
        risk_score=float(option_row.get("risk_score") or 0),
        suitability_notes="Estrutura direcional de baixa/proteção para estudo; risco limitado ao prêmio.",
    )


def build_bull_call_spread(chain_df: pd.DataFrame, underlying: str, maturity_date: str) -> dict[str, Any] | None:
    calls = chain_df[(chain_df["underlying"] == underlying) & (chain_df["maturity_date"].astype(str) == str(maturity_date)) & (chain_df["option_type"] == "CALL")].sort_values("strike")
    if len(calls) < 2:
        return None
    buy = calls.iloc[0]
    sell = calls.iloc[1]
    debit = max(_price(buy) - _price(sell), 0)
    width = float(sell["strike"] - buy["strike"])
    return _structure(
        "BULL_CALL_SPREAD",
        underlying,
        str(maturity_date),
        [_leg(buy, "BUY"), _leg(sell, "SELL")],
        net_debit=debit * CONTRACT_SIZE,
        max_profit=max(width - debit, 0) * CONTRACT_SIZE,
        max_loss=debit * CONTRACT_SIZE,
        breakeven=float(buy["strike"]) + debit,
        risk_score=float(np.mean([buy.get("risk_score", 0), sell.get("risk_score", 0)])),
        suitability_notes="Trava de alta com risco definido; estrutura potencial a estudar.",
    )


def build_bear_put_spread(chain_df: pd.DataFrame, underlying: str, maturity_date: str) -> dict[str, Any] | None:
    puts = chain_df[(chain_df["underlying"] == underlying) & (chain_df["maturity_date"].astype(str) == str(maturity_date)) & (chain_df["option_type"] == "PUT")].sort_values("strike", ascending=False)
    if len(puts) < 2:
        return None
    buy = puts.iloc[0]
    sell = puts.iloc[1]
    debit = max(_price(buy) - _price(sell), 0)
    width = float(buy["strike"] - sell["strike"])
    return _structure(
        "BEAR_PUT_SPREAD",
        underlying,
        str(maturity_date),
        [_leg(buy, "BUY"), _leg(sell, "SELL")],
        net_debit=debit * CONTRACT_SIZE,
        max_profit=max(width - debit, 0) * CONTRACT_SIZE,
        max_loss=debit * CONTRACT_SIZE,
        breakeven=float(buy["strike"]) - debit,
        risk_score=float(np.mean([buy.get("risk_score", 0), sell.get("risk_score", 0)])),
        suitability_notes="Trava de baixa com risco definido; estrutura potencial a estudar.",
    )


def calculate_structure_payoff(structure: dict[str, Any], price_range) -> pd.DataFrame:
    legs = json.loads(structure.get("legs_json") or "[]")
    rows = []
    for price in price_range:
        payoff = 0.0
        for leg in legs:
            intrinsic = max(price - leg["strike"], 0) if leg["option_type"] == "CALL" else max(leg["strike"] - price, 0)
            sign = 1 if leg["direction"] == "BUY" else -1
            payoff += sign * (intrinsic - leg["price"]) * leg.get("quantity", 1) * CONTRACT_SIZE
        rows.append({"underlying_price": price, "payoff": payoff})
    return pd.DataFrame(rows)


def calculate_max_profit(structure: dict[str, Any]) -> float:
    return float(structure.get("max_profit", math.nan))


def calculate_max_loss(structure: dict[str, Any]) -> float:
    return float(structure.get("max_loss", math.nan))


def calculate_breakeven_points(structure: dict[str, Any]) -> list[float]:
    value = structure.get("breakeven")
    return [] if value is None or pd.isna(value) else [float(value)]


def calculate_risk_reward(structure: dict[str, Any]) -> float:
    max_profit = structure.get("max_profit")
    max_loss = structure.get("max_loss")
    try:
        if max_loss and max_loss > 0 and not math.isinf(max_profit):
            return round(float(max_profit) / float(max_loss), 4)
        if max_loss and max_loss > 0 and math.isinf(max_profit):
            return 999.0
    except TypeError:
        pass
    return 0.0


def classify_structure_risk(structure: dict[str, Any]) -> str:
    max_loss = structure.get("max_loss")
    if max_loss is None or pd.isna(max_loss):
        return "DADOS_INSUFICIENTES"
    if math.isinf(float(max_loss)):
        return "RISCO_ILIMITADO"
    if float(max_loss) <= 0:
        return "RISCO_BAIXO"
    if float(structure.get("payoff_ratio") or 0) >= 1:
        return "RISCO_DEFINIDO"
    return "RISCO_ELEVADO"
