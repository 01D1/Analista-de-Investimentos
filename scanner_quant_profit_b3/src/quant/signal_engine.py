"""
Signal Engine — Quant Research Layer.

Transforma cada oportunidade em um vetor de features e gera:
  - score probabilístico 0-100
  - classificação: COMPRA / OBSERVAR / DESCARTAR
  - explicação por que o setup foi aprovado ou rejeitado

Módulo em duas camadas:
  1. Condições básicas (trend, momentum, volume, volatility) — retornam 0-100
  2. Score probabilístico via FeatureVector — combina todas as features
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import sma, ema, rsi, atr, macd
from .volatility import historical_volatility


# ---------------------------------------------------------------------------
# Condição de tendência
# ---------------------------------------------------------------------------

def trend_condition(close: pd.Series, fast: int = 9, slow: int = 21) -> dict:
    if len(close) < slow:
        return {"trend": "INDEFINIDA", "trend_score": 0, "sma_fast": 0.0, "sma_slow": 0.0}

    sma_fast = sma(close, fast)
    sma_slow = sma(close, slow)
    last_close = float(close.iloc[-1])
    last_fast = float(sma_fast.iloc[-1])
    last_slow = float(sma_slow.iloc[-1])

    score = 0
    if last_close > last_slow:
        score += 40
    if last_close > last_fast:
        score += 30
    if last_fast > last_slow:
        score += 30

    if score >= 90:
        trend = "ALTA"
    elif score >= 60:
        trend = "ALTA_PARCIAL"
    elif score == 0:
        trend = "QUEDA"
    else:
        trend = "LATERAL"

    return {
        "trend": trend,
        "trend_score": score,
        "sma_fast": round(last_fast, 4),
        "sma_slow": round(last_slow, 4),
        "price_vs_sma_fast_pct": round((last_close / last_fast - 1) * 100, 2) if last_fast else 0.0,
    }


# ---------------------------------------------------------------------------
# Condição de momentum
# ---------------------------------------------------------------------------

def momentum_condition(close: pd.Series, period: int = 14) -> dict:
    if len(close) < period + 5:
        return {"momentum_condition": "SEM_DADOS", "momentum_score": 0, "rsi": 50.0}

    rsi_vals = rsi(close, period)
    last_rsi = float(rsi_vals.iloc[-1])

    macd_line, signal_line, hist = macd(close)
    last_hist = float(hist.iloc[-1]) if not hist.empty else 0.0

    if last_rsi >= 70:
        rsi_score, rsi_condition = 0, "SOBRECOMPRADO"
    elif last_rsi >= 60:
        rsi_score, rsi_condition = 90, "FORTE"
    elif last_rsi >= 50:
        rsi_score, rsi_condition = 70, "POSITIVO"
    elif last_rsi >= 40:
        rsi_score, rsi_condition = 40, "NEUTRO"
    elif last_rsi >= 30:
        rsi_score, rsi_condition = 20, "FRACO"
    else:
        rsi_score, rsi_condition = 5, "SOBREVENDIDO"

    score = min(rsi_score + (10 if last_hist > 0 else 0), 100)

    return {
        "momentum_condition": rsi_condition,
        "momentum_score": score,
        "rsi": round(last_rsi, 2),
        "macd_hist": round(last_hist, 4),
    }


# ---------------------------------------------------------------------------
# Condição de volume
# ---------------------------------------------------------------------------

def volume_condition(volume: pd.Series, window: int = 20) -> dict:
    if len(volume) < 3:
        return {"volume_condition": "SEM_DADOS", "volume_score": 0, "volume_ratio": 1.0}

    avg_vol = sma(volume, min(window, len(volume)))
    last_vol = float(volume.iloc[-1])
    last_avg = float(avg_vol.iloc[-1])
    ratio = last_vol / last_avg if last_avg > 0 else 1.0

    if ratio >= 2.5:
        condition, score = "EXPLOSIVO", 100
    elif ratio >= 1.8:
        condition, score = "MUITO_ALTO", 85
    elif ratio >= 1.3:
        condition, score = "ALTO", 70
    elif ratio >= 0.8:
        condition, score = "NORMAL", 50
    else:
        condition, score = "BAIXO", 20

    return {
        "volume_condition": condition,
        "volume_score": score,
        "volume_ratio": round(ratio, 2),
        "volume_last": round(last_vol, 0),
    }


# ---------------------------------------------------------------------------
# Condição de volatilidade
# ---------------------------------------------------------------------------

def volatility_condition(close: pd.Series, window: int = 21) -> dict:
    if len(close) < 5:
        return {"vol_condition": "SEM_DADOS", "vol_score": 50, "hist_vol": 0.0}

    hv = historical_volatility(close, window=min(window, len(close) - 1))
    last_hv = float(hv.dropna().iloc[-1]) if not hv.dropna().empty else 0.30

    if last_hv < 0.10:
        condition, score = "MUITO_BAIXA", 30
    elif last_hv < 0.20:
        condition, score = "BAIXA", 60
    elif last_hv < 0.35:
        condition, score = "MEDIA", 100
    elif last_hv < 0.55:
        condition, score = "ALTA", 75
    else:
        condition, score = "MUITO_ALTA", 35

    return {
        "vol_condition": condition,
        "vol_score": score,
        "hist_vol": round(last_hv, 4),
        "hist_vol_pct": round(last_hv * 100, 2),
    }


# ---------------------------------------------------------------------------
# Score probabilístico via FeatureVector
# ---------------------------------------------------------------------------

def compute_probabilistic_score(
    fv: "FeatureVector",
    qcfg: dict,
) -> dict:
    """
    Gera um score probabilístico 0-100 a partir de um FeatureVector completo.

    Vai além do score ponderado simples: usa relações não-lineares entre
    features para detectar setups de qualidade superior.

    Retorna:
        score         — score final 0-100
        confidence    — ALTA / MEDIA / BAIXA
        signal        — COMPRA / OBSERVAR / DESCARTAR
        component_scores — dict com scores por dimensão
        reasons_for   — features que favorecem o setup
        reasons_against — features que prejudicam
    """
    sf = fv.stock
    of = fv.option
    weights = qcfg.get("score_weights", {})

    # ---- Componentes de score ----------------------------------------

    # 1. Tendência (0-100)
    trend_score = _score_trend(sf)

    # 2. Momentum (0-100)
    momentum_score = _score_momentum(sf)

    # 3. Volume (0-100)
    volume_score = _score_volume(sf)

    # 4. Volatilidade (0-100)
    vol_score = _score_volatility(sf)

    # 5. Liquidez da opção (0-100)
    liq_score = float(of.liq_score)

    # 6. Moneyness (0-100)
    moneyness_score = _score_moneyness(of, fv.option_type)

    # 7. DTE (0-100)
    min_dte = qcfg.get("min_dte", 15)
    max_dte = qcfg.get("max_dte", 45)
    dte_score = _score_dte(of.dte, min_dte, max_dte)

    # 8. Bônus por alinhamento múltiplo de features
    alignment_bonus = _alignment_bonus(sf, of, fv.option_type)

    # ---- Score ponderado ------------------------------------------------
    w = {
        "stock_trend_score": weights.get("stock_trend_score", 0.25),
        "stock_momentum_score": weights.get("stock_momentum_score", 0.20),
        "stock_volume_score": weights.get("stock_volume_score", 0.15),
        "option_liquidity_score": weights.get("option_liquidity_score", 0.20),
        "option_moneyness_score": weights.get("option_moneyness_score", 0.10),
        "option_dte_score": weights.get("option_dte_score", 0.10),
    }

    weighted_score = (
        trend_score * w["stock_trend_score"]
        + momentum_score * w["stock_momentum_score"]
        + volume_score * w["stock_volume_score"]
        + liq_score * w["option_liquidity_score"]
        + moneyness_score * w["option_moneyness_score"]
        + dte_score * w["option_dte_score"]
    )

    final_score = min(round(weighted_score + alignment_bonus, 2), 100.0)

    # ---- Classificação ---------------------------------------------------
    sc_validated = qcfg.get("score_entrada_validada", 70)
    sc_watch = qcfg.get("score_aguardar", 50)

    if final_score >= sc_validated:
        signal = "COMPRA"
        confidence = "ALTA" if final_score >= 80 else "MEDIA"
    elif final_score >= sc_watch:
        signal = "OBSERVAR"
        confidence = "MEDIA" if final_score >= 60 else "BAIXA"
    else:
        signal = "DESCARTAR"
        confidence = "BAIXA"

    # ---- Explicações -------------------------------------------------------
    reasons_for, reasons_against = _explain_features(sf, of, fv.option_type, qcfg)

    return {
        "score": final_score,
        "signal": signal,
        "confidence": confidence,
        "component_scores": {
            "tendencia": trend_score,
            "momentum": momentum_score,
            "volume": volume_score,
            "volatilidade": vol_score,
            "liquidez_opcao": liq_score,
            "moneyness": moneyness_score,
            "dte": dte_score,
            "bonus_alinhamento": alignment_bonus,
        },
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
    }


def _score_trend(sf: "StockFeatures") -> float:
    score = 0.0
    # Retorno de curto prazo alinhado com tendência
    if sf.ret_5 > 0:
        score += 30
    if sf.ret_20 > 0:
        score += 30
    # Posição no range — acima de 60% favorável para tendência de alta
    if sf.range_pos > 0.6:
        score += 20
    # Distância da SMA20 — ideal entre +0.5% e +5%
    if 0.5 <= sf.dist_sma20 <= 5.0:
        score += 20
    elif sf.dist_sma20 > 5.0:
        score += 10  # longe da média = risco de pullback
    return min(score, 100.0)


def _score_momentum(sf: "StockFeatures") -> float:
    # Retorno de curto prazo
    score = 0.0
    if sf.ret_1 > 0:
        score += 15
    if sf.ret_3 > 0:
        score += 20
    if sf.ret_5 > 0:
        score += 20
    # Aceleração: ret_1 > ret_5/5 (momentum aumentando)
    if sf.ret_1 > 0 and sf.ret_5 / 5 < sf.ret_1:
        score += 15
    if sf.high_break_20 == 1.0:
        score += 30  # rompimento de máxima = momentum forte
    return min(score, 100.0)


def _score_volume(sf: "StockFeatures") -> float:
    r = sf.volume_ratio
    if r >= 2.5:
        return 100.0
    if r >= 1.8:
        return 85.0
    if r >= 1.3:
        return 70.0
    if r >= 0.8:
        return 50.0
    return 20.0


def _score_volatility(sf: "StockFeatures") -> float:
    hv = sf.vol_20
    if hv < 0.10:
        return 30.0
    if hv < 0.20:
        return 60.0
    if hv < 0.35:
        return 100.0
    if hv < 0.55:
        return 75.0
    return 35.0


def _score_moneyness(of: "OptionFeatures", option_type: str) -> float:
    m = of.moneyness_pct
    if option_type == "CALL":
        if 0.0 <= m <= 7.0:
            return 100.0
        if -2.0 <= m < 0.0:
            return 85.0
        if 7.0 < m <= 15.0:
            return 60.0
        return 15.0
    else:
        if -7.0 <= m <= 0.0:
            return 100.0
        if 0.0 < m <= 2.0:
            return 85.0
        if -15.0 <= m < -7.0:
            return 60.0
        return 15.0


def _score_dte(dte: int, min_dte: int, max_dte: int) -> float:
    ideal = (min_dte + max_dte) / 2.0
    return max(0.0, 100.0 - abs(dte - ideal) * 3.5)


def _alignment_bonus(sf: "StockFeatures", of: "OptionFeatures", option_type: str) -> float:
    """
    Bônus quando múltiplos sinais independentes apontam na mesma direção.
    Máx +10 pontos.
    """
    positive_signals = 0
    if sf.ret_5 > 0:
        positive_signals += 1
    if sf.ret_20 > 0:
        positive_signals += 1
    if sf.volume_ratio > 1.2:
        positive_signals += 1
    if sf.high_break_20 == 1.0:
        positive_signals += 1
    if sf.range_pos > 0.65:
        positive_signals += 1
    if -2 <= of.moneyness_pct <= 7 and option_type == "CALL":
        positive_signals += 1

    if positive_signals >= 5:
        return 10.0
    if positive_signals >= 4:
        return 5.0
    if positive_signals >= 3:
        return 2.0
    return 0.0


def _explain_features(
    sf: "StockFeatures",
    of: "OptionFeatures",
    option_type: str,
    qcfg: dict,
) -> tuple[list[str], list[str]]:
    reasons_for = []
    reasons_against = []

    # Tendência
    if sf.ret_20 > 2.0:
        reasons_for.append(f"Retorno 20d positivo ({sf.ret_20:+.1f}%)")
    if sf.high_break_20 == 1.0:
        reasons_for.append("Rompimento de máxima dos últimos 20 períodos")
    if 0.5 <= sf.dist_sma20 <= 5.0:
        reasons_for.append(f"Preço {sf.dist_sma20:+.1f}% acima da SMA20 — tendência saudável")

    # Momentum
    if sf.ret_1 > 0 and sf.ret_3 > 0 and sf.ret_5 > 0:
        reasons_for.append("Retornos de curto prazo alinhados (1d, 3d, 5d positivos)")
    if sf.range_pos > 0.70:
        reasons_for.append(f"Preço no topo do range ({sf.range_pos*100:.0f}% do range 20d)")

    # Volume
    if sf.volume_ratio >= 1.5:
        reasons_for.append(f"Volume {sf.volume_ratio:.1f}x acima da média — pressão compradora")

    # Opção
    if abs(of.moneyness_pct) <= 3 and option_type == "CALL":
        reasons_for.append(f"CALL ATM — melhor relação prêmio/delta")
    if of.liq_score >= 80:
        reasons_for.append(f"Alta liquidez ({of.liq_score:.0f}/100)")
    if 20 <= of.dte <= 35:
        reasons_for.append(f"DTE {of.dte}d — zona ideal de theta/gamma")

    # Contrários
    if sf.ret_20 < -5.0:
        reasons_against.append(f"Retorno 20d negativo ({sf.ret_20:+.1f}%) — tendência de baixa")
    if sf.dist_sma20 > 8.0:
        reasons_against.append(f"Preço {sf.dist_sma20:.1f}% acima da SMA20 — risco de pullback")
    if sf.vol_20 > 0.55:
        reasons_against.append(f"Volatilidade muito alta ({sf.vol_20*100:.0f}%) — prêmio caro")
    if sf.vol_20 < 0.10:
        reasons_against.append(f"Volatilidade muito baixa ({sf.vol_20*100:.0f}%) — prêmio sem valor")
    if of.dte < 10:
        reasons_against.append(f"DTE muito curto ({of.dte}d) — theta acelerado")
    if of.spread_pct > 0.08:
        reasons_against.append(f"Spread estimado alto ({of.spread_pct*100:.1f}%) — custo de entrada elevado")
    if of.liq_score < 40:
        reasons_against.append(f"Baixa liquidez ({of.liq_score:.0f}/100) — risco de saída difícil")

    return reasons_for, reasons_against


# ---------------------------------------------------------------------------
# Interface de alto nível: classifica um setup completo
# ---------------------------------------------------------------------------

def classify_signal(score: float, qcfg: dict) -> str:
    """Retorna COMPRA / OBSERVAR / DESCARTAR a partir do score."""
    if score >= qcfg.get("score_entrada_validada", 70):
        return "COMPRA"
    if score >= qcfg.get("score_aguardar", 50):
        return "OBSERVAR"
    return "DESCARTAR"
