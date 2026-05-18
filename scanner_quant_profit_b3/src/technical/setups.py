"""Deteccao parametrizada de setups tecnicos para estudo."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


SETUP_TYPES = [
    "BREAKOUT_VOLUME",
    "BREAKDOWN_VOLUME",
    "PULLBACK_TREND",
    "MEAN_REVERSION",
    "MOMENTUM_CONTINUATION",
    "VOLATILITY_SQUEEZE",
    "VWAP_RECLAIM",
    "RELATIVE_STRENGTH_LEADER",
    "OVERSOLD_REVERSAL",
    "RANGE_EXPANSION",
]


def _num(row: pd.Series, key: str, default: float = 0) -> float:
    value = pd.to_numeric(pd.Series([row.get(key, default)]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else default


def _add(rows: list[dict[str, Any]], row: pd.Series, setup_type: str, score: float, confidence: float, direction: str, reasons: list[str], against: list[str] | None = None) -> None:
    close = _num(row, "close")
    atr = _num(row, "atr_14", close * 0.02 if close else 0)
    rows.append(
        {
            "trade_date": str(row.get("trade_date", ""))[:10],
            "ticker": row.get("ticker", ""),
            "setup_type": setup_type,
            "setup_score": round(float(max(0, min(100, score))), 2),
            "setup_confidence": round(float(max(0, min(1, confidence))), 4),
            "setup_direction": direction,
            "trigger_price": close,
            "invalidation_price": close - atr if direction == "BULLISH" else close + atr if direction == "BEARISH" else close,
            "target_hint": close + 2 * atr if direction == "BULLISH" else close - 2 * atr if direction == "BEARISH" else close,
            "risk_hint": atr,
            "reasons_for": json.dumps(reasons, ensure_ascii=False),
            "reasons_against": json.dumps(against or [], ensure_ascii=False),
            "metadata_json": "{}",
        }
    )


def detect_technical_setups(features_df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    columns = [
        "trade_date",
        "ticker",
        "setup_type",
        "setup_score",
        "setup_confidence",
        "setup_direction",
        "trigger_price",
        "invalidation_price",
        "target_hint",
        "risk_hint",
        "reasons_for",
        "reasons_against",
        "metadata_json",
    ]
    if features_df.empty:
        return pd.DataFrame(columns=columns)
    cfg = config or {}
    min_score = float(cfg.get("min_setup_score", 0))
    rows: list[dict[str, Any]] = []
    for _, row in features_df.iterrows():
        trend = str(row.get("trend_short", ""))
        momentum = str(row.get("momentum_state", ""))
        vol = str(row.get("volatility_regime", ""))
        rv = _num(row, "relative_volume_20", 1)
        tech = _num(row, "technical_score_final", 50)
        rsi = _num(row, "rsi_14", 50)
        if bool(row.get("breakout_20", False)) and rv >= 1.3:
            _add(rows, row, "BREAKOUT_VOLUME", max(tech, 70), min(0.95, 0.45 + rv / 4), "BULLISH", ["Fechamento acima da resistencia objetiva", f"Volume relativo {rv:.2f}x"])
        if bool(row.get("breakdown_20", False)) and rv >= 1.3:
            _add(rows, row, "BREAKDOWN_VOLUME", max(55, 100 - tech), min(0.95, 0.45 + rv / 4), "BEARISH", ["Fechamento abaixo do suporte objetivo", f"Volume relativo {rv:.2f}x"])
        if trend == "ALTA_TENDENCIAL" and bool(row.get("near_support_20", False)) and rsi >= 40:
            _add(rows, row, "PULLBACK_TREND", tech, 0.65, "BULLISH", ["Tendencia curta positiva", "Preco proximo a suporte objetivo"])
        if rsi <= 30 or _num(row, "distance_to_low_20", 99) <= 2:
            _add(rows, row, "MEAN_REVERSION", 60 + (30 - min(rsi, 30)), 0.55, "BULLISH", ["RSI ou distancia ao suporte sugere esticamento"], ["Setup exige confirmacao posterior"])
        if trend == "ALTA_TENDENCIAL" and momentum in {"MOMENTUM_FORTE", "MOMENTUM_MODERADO", "SOBRECOMPRADO"}:
            _add(rows, row, "MOMENTUM_CONTINUATION", tech, 0.6, "BULLISH", ["Tendencia e momentum alinhados"])
        if vol == "COMPRESSAO_VOLATILIDADE":
            _add(rows, row, "VOLATILITY_SQUEEZE", 55 + min(30, _num(row, "volume_score") / 3), 0.5, "NEUTRAL", ["Compressao objetiva de volatilidade"])
        if "vwap" in row.index and _num(row, "close") > _num(row, "vwap"):
            _add(rows, row, "VWAP_RECLAIM", 58, 0.5, "BULLISH", ["Preco acima do VWAP acumulado"])
        if tech >= 75 and trend == "ALTA_TENDENCIAL":
            _add(rows, row, "RELATIVE_STRENGTH_LEADER", tech, 0.6, "BULLISH", ["Score tecnico elevado e tendencia positiva"])
        if rsi < 35 and bool(row.get("reversal_candle", False)):
            _add(rows, row, "OVERSOLD_REVERSAL", 65, 0.55, "BULLISH", ["Sobrevenda objetiva com candle de reversao"])
        if bool(row.get("wide_range_bar", False)) and rv >= 1.2:
            direction = "BULLISH" if _num(row, "close") >= _num(row, "open") else "BEARISH"
            _add(rows, row, "RANGE_EXPANSION", 62, 0.55, direction, ["Range acima da media com volume acima da media"])
    out = pd.DataFrame(rows, columns=columns)
    if out.empty:
        return out
    return out[pd.to_numeric(out["setup_score"], errors="coerce").fillna(0) >= min_score].reset_index(drop=True)

