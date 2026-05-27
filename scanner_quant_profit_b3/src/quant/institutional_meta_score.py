"""
Institutional Meta Score — Pontuação institucional multi-camada.

Combina todos os layers do Radar Macro em um único score:
  quant_score              : técnico (momentum, tendência, liquidez, vol)
  flow_score               : fluxo (conviction, pressure, unusual)
  volatility_score         : vol implícita vs histórica (IV analytics)
  macro_score              : regime macro (headwind/tailwind)
  regime_score             : intensidade de regime (market_regime_engine)
  valuation_score          : valuation relativo (PE, PB, upside DCF)
  political_score          : risco político/regulatório (proxy CDS + eventos)
  liquidity_score          : liquidez de mercado (ADTV, spread)
  fundamental_confirmation : balanço, earnings quality (confirmação fundamental)

Saída:
  institutional_meta_score : 0–100
  conviction_tier          : S | A | B | C | D
  signal_direction         : BUY | HOLD | SELL | WATCH
  explainability           : dict com razões estruturadas

Regra de uso: LLM usa esses campos como input de síntese — nunca calcula.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Estrutura de saída
# ---------------------------------------------------------------------------

@dataclass
class MetaScoreResult:
    ticker: str

    # Scores por dimensão (0–100)
    quant_score: float
    flow_score: float
    volatility_score: float
    macro_score: float
    regime_score: float
    valuation_score: float
    political_score: float
    liquidity_score: float
    fundamental_confirmation: float

    # Meta-score final
    institutional_meta_score: float

    # Classificação
    conviction_tier: str       # S | A | B | C | D
    signal_direction: str      # BUY | HOLD | SELL | WATCH
    confidence: float          # 0–1 (quão confiáveis são os inputs)

    # Explicabilidade
    top_bullish_factors: list[str] = field(default_factory=list)
    top_bearish_factors: list[str] = field(default_factory=list)
    data_quality_flag: str = "OK"    # OK | DEGRADED | UNRELIABLE
    explainability: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


# ---------------------------------------------------------------------------
# Pesos por dimensão (calibrados para mercado brasileiro)
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS = {
    "quant_score":              0.22,   # técnico — alto peso por disponibilidade
    "flow_score":               0.18,   # fluxo institucional
    "volatility_score":         0.10,   # contexto de vol
    "macro_score":              0.15,   # regime macro Brasil
    "regime_score":             0.08,   # intensidade de regime (local)
    "valuation_score":          0.10,   # múltiplos e upside
    "political_score":          0.05,   # risco político
    "liquidity_score":          0.08,   # liquidez operacional
    "fundamental_confirmation": 0.04,   # confirmação fundamentalista
}

# Tier mapping por score
_TIER_BREAKS = [
    (85, "S"),
    (72, "A"),
    (58, "B"),
    (42, "C"),
    (0,  "D"),
]

_SIGNAL_BREAKS = [
    (68, "BUY"),
    (50, "WATCH"),
    (35, "HOLD"),
    (0,  "SELL"),
]


def _clip(v: float) -> float:
    return float(np.clip(v, 0.0, 100.0))


def _tier(score: float) -> str:
    for threshold, label in _TIER_BREAKS:
        if score >= threshold:
            return label
    return "D"


def _signal(score: float, macro_headwind: float = 0.0) -> str:
    # Headwind macro muito elevado bloqueia BUY
    if macro_headwind >= 75 and score >= 68:
        return "WATCH"
    for threshold, label in _SIGNAL_BREAKS:
        if score >= threshold:
            return label
    return "SELL"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def compute_meta_score(
    ticker: str,
    *,
    quant_score: float = 50.0,
    flow_score: float = 50.0,
    volatility_score: float = 50.0,
    macro_score: float = 50.0,
    regime_score: float = 50.0,
    valuation_score: float = 50.0,
    political_score: float = 70.0,
    liquidity_score: float = 60.0,
    fundamental_confirmation: float = 50.0,
    # Contexto adicional para ajuste e explicabilidade
    macro_headwind: float = 50.0,
    macro_tailwind: float = 50.0,
    iv_regime: str = "NORMAL",
    flow_conviction: float = 50.0,
    ev_score: float = 50.0,
    data_quality_score: float = 100.0,
    weights: dict[str, float] | None = None,
) -> MetaScoreResult:
    """
    Calcula o institutional_meta_score combinando todos os layers.

    Scores de entrada devem estar em [0–100].
    Valores ausentes → usar 50.0 (neutro), não 0.
    """
    w = {**_DEFAULT_WEIGHTS, **(weights or {})}

    # Normaliza pesos
    total_w = sum(w.values())
    w = {k: v / total_w for k, v in w.items()}

    scores = {
        "quant_score":              _clip(quant_score),
        "flow_score":               _clip(flow_score),
        "volatility_score":         _clip(volatility_score),
        "macro_score":              _clip(macro_score),
        "regime_score":             _clip(regime_score),
        "valuation_score":          _clip(valuation_score),
        "political_score":          _clip(political_score),
        "liquidity_score":          _clip(liquidity_score),
        "fundamental_confirmation": _clip(fundamental_confirmation),
    }

    raw_meta = sum(scores[k] * w[k] for k in scores)

    # Penalidade por qualidade de dados degradada
    dq = float(np.clip(data_quality_score, 0, 100))
    if dq < 60:
        dq_penalty = (60 - dq) / 60 * 15    # até -15 pontos
    elif dq < 80:
        dq_penalty = (80 - dq) / 80 * 7
    else:
        dq_penalty = 0.0

    # Bônus de alinhamento multi-layer (≥4 layers > 65 = convergência real)
    layers_bullish = sum(1 for v in scores.values() if v >= 65)
    layers_bearish = sum(1 for v in scores.values() if v <= 35)
    if layers_bullish >= 6:
        alignment_bonus = 5.0
    elif layers_bullish >= 4:
        alignment_bonus = 2.5
    elif layers_bearish >= 6:
        alignment_bonus = -5.0
    elif layers_bearish >= 4:
        alignment_bonus = -2.5
    else:
        alignment_bonus = 0.0

    meta = _clip(raw_meta - dq_penalty + alignment_bonus)

    # Confiança: baseada em quantos layers têm dados reais (vs 50 neutro hardcoded)
    non_neutral = sum(1 for v in scores.values() if v != 50.0)
    confidence = round(non_neutral / len(scores), 2)

    # Data quality flag
    if dq < 60:
        dq_flag = "UNRELIABLE"
    elif dq < 80:
        dq_flag = "DEGRADED"
    else:
        dq_flag = "OK"

    # Fatores bullish/bearish (top 3 de cada lado)
    factor_map = {
        "quant_score":              ("momentum e tendência técnica", "fraqueza técnica"),
        "flow_score":               ("fluxo institucional comprador", "pressão vendedora institucional"),
        "volatility_score":         ("vol implícita favorável", "vol implícita adversa"),
        "macro_score":              ("ambiente macro favorável", "headwind macro"),
        "regime_score":             ("regime de alta intensidade positivo", "regime adverso"),
        "valuation_score":          ("valuation descontado", "valuation esticado"),
        "political_score":          ("risco político baixo", "risco político elevado"),
        "liquidity_score":          ("liquidez operacional forte", "liquidez fraca"),
        "fundamental_confirmation": ("fundamentos sólidos", "fundamentos frágeis"),
    }

    bullish = sorted(
        [(k, scores[k]) for k in scores if scores[k] >= 60],
        key=lambda x: x[1], reverse=True,
    )
    bearish = sorted(
        [(k, scores[k]) for k in scores if scores[k] <= 40],
        key=lambda x: x[1],
    )

    top_bullish = [factor_map[k][0] for k, _ in bullish[:3]]
    top_bearish = [factor_map[k][1] for k, _ in bearish[:3]]

    # IV extrema como fator destaque
    if iv_regime == "EXTREMA":
        top_bearish.insert(0, "IV percentile extremo (vol cara)")
    elif iv_regime == "COMPRIMIDA":
        top_bullish.insert(0, "IV comprimida (oportunidade de vol barata)")

    # EV como fator
    if ev_score >= 70:
        top_bullish.append(f"EV score {ev_score:.0f}/100 (assimetria favorável)")
    elif ev_score <= 30:
        top_bearish.append(f"EV score {ev_score:.0f}/100 (assimetria desfavorável)")

    explainability = {
        "scores_by_dimension": {k: round(v, 1) for k, v in scores.items()},
        "weights": {k: round(v, 3) for k, v in w.items()},
        "raw_weighted": round(raw_meta, 1),
        "dq_penalty": round(dq_penalty, 1),
        "alignment_bonus": round(alignment_bonus, 1),
        "final_meta_score": round(meta, 1),
        "layers_bullish": layers_bullish,
        "layers_bearish": layers_bearish,
        "macro_headwind": macro_headwind,
        "macro_tailwind": macro_tailwind,
        "iv_regime": iv_regime,
        "ev_score": ev_score,
        "data_quality_score": dq,
    }

    return MetaScoreResult(
        ticker=ticker,
        quant_score=round(scores["quant_score"], 1),
        flow_score=round(scores["flow_score"], 1),
        volatility_score=round(scores["volatility_score"], 1),
        macro_score=round(scores["macro_score"], 1),
        regime_score=round(scores["regime_score"], 1),
        valuation_score=round(scores["valuation_score"], 1),
        political_score=round(scores["political_score"], 1),
        liquidity_score=round(scores["liquidity_score"], 1),
        fundamental_confirmation=round(scores["fundamental_confirmation"], 1),
        institutional_meta_score=round(meta, 1),
        conviction_tier=_tier(meta),
        signal_direction=_signal(meta, macro_headwind),
        confidence=confidence,
        top_bullish_factors=top_bullish,
        top_bearish_factors=top_bearish,
        data_quality_flag=dq_flag,
        explainability=explainability,
    )


# ---------------------------------------------------------------------------
# Adapter: integra com scoring.py existente
# ---------------------------------------------------------------------------

def from_scoring_result(
    ticker: str,
    scoring_result: dict,
    *,
    flow_result=None,        # FlowResult de flow_engine.py
    regime_snapshot=None,    # RegimeSnapshot de market_regime_engine.py
    ev_result=None,          # EVResult de expected_value_engine.py
    institutional_flow=None, # InstitutionalFlowResult de flow_institutional.py
    valuation_upside_pct: float = 0.0,
    fundamental_score: float = 50.0,
    data_quality_score: float = 100.0,
) -> MetaScoreResult:
    """
    Cria um MetaScoreResult a partir dos outputs dos módulos existentes.
    Todos os parâmetros além de ticker/scoring_result são opcionais.
    """
    quant = float(scoring_result.get("score_final", 50.0))

    # Flow: converte FlowResult (-100,+100) → (0,100)
    flow = 50.0
    if flow_result is not None:
        raw_flow = float(getattr(flow_result, "score", 0))
        flow = _clip((raw_flow + 100.0) / 2.0)

    # Flow institucional
    flow_conviction = 50.0
    iv_regime = "NORMAL"
    if institutional_flow is not None:
        flow_conviction = float(getattr(institutional_flow, "flow_conviction_score", 50.0))
        iv_regime = str(getattr(institutional_flow, "iv_regime", "NORMAL"))
        # Combina flow básico com conviction institucional
        flow = _clip(flow * 0.5 + flow_conviction * 0.5)

    # Macro
    macro_score = 50.0
    regime_sc = 50.0
    macro_headwind = 50.0
    macro_tailwind = 50.0
    if regime_snapshot is not None:
        macro_headwind = float(getattr(regime_snapshot, "macro_headwind", 50.0))
        macro_tailwind = float(getattr(regime_snapshot, "macro_tailwind", 50.0))
        macro_score = _clip(100.0 - macro_headwind)
        regime_sc = float(getattr(regime_snapshot, "regime_score", 50.0))

    # Valuation: upside DCF > 30% → score alto
    val_score = _clip(50.0 + valuation_upside_pct * 1.5)

    # EV
    ev_score = float(getattr(ev_result, "expected_value_score", 50.0)) if ev_result else 50.0

    # Volatility score: usa IV regime para orientar
    vol_score_map = {"COMPRIMIDA": 75, "NORMAL": 55, "EXPANDIDA": 40, "EXTREMA": 25}
    vol_score = float(vol_score_map.get(iv_regime, 55))

    return compute_meta_score(
        ticker=ticker,
        quant_score=quant,
        flow_score=flow,
        volatility_score=vol_score,
        macro_score=macro_score,
        regime_score=regime_sc,
        valuation_score=val_score,
        political_score=70.0,               # default conservador
        liquidity_score=float(scoring_result.get("score_liquidez", 60.0)),
        fundamental_confirmation=fundamental_score,
        macro_headwind=macro_headwind,
        macro_tailwind=macro_tailwind,
        iv_regime=iv_regime,
        flow_conviction=flow_conviction,
        ev_score=ev_score,
        data_quality_score=data_quality_score,
    )
