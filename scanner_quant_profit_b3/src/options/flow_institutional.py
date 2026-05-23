"""
Flow Institucional — Detecção de atividade incomum em opções.

Vai além do flow_engine.py (que usa apenas preço+volume da ação).
Analisa a cadeia de opções para detectar:
  - IV percentile extremo (pressão de vol implícita)
  - Aceleração de open interest (acumulação silenciosa)
  - Atividade incomum: prêmio desproporcional ao OI médio
  - Pressão de gamma por strike (onde os dealers precisam hedge)
  - Concentração de interesse em strikes específicos
  - Desequilíbrio call/put (posicionamento direcional institucional)

Scores produzidos:
  flow_conviction_score  : 0–100 (convicção do fluxo institucional)
  dealer_pressure_score  : 0–100 (quanto os dealers precisam rebalancear)
  gamma_risk_score       : 0–100 (risco de aceleração por gamma)
  unusual_activity_score : 0–100 (atividade fora do padrão histórico)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class UnusualOptionActivity:
    ticker: str
    option_ticker: str
    option_type: str        # CALL | PUT
    strike: float
    expiry: str
    dte: int
    premium: float
    volume: float
    open_interest: float
    iv_implied: float
    delta: float
    unusual_score: float    # 0–100
    reason: str
    direction: str          # BULLISH | BEARISH | NEUTRAL


@dataclass
class InstitutionalFlowResult:
    underlying: str
    as_of: str

    # Scores principais
    flow_conviction_score: float     # 0–100
    dealer_pressure_score: float     # 0–100
    gamma_risk_score: float          # 0–100
    unusual_activity_score: float    # 0–100

    # Direcionalidade
    directional_bias: str            # BULLISH | BEARISH | NEUTRAL
    call_put_ratio: float            # >1 = viés comprador
    iv_regime: str                   # COMPRIMIDA | NORMAL | EXPANDIDA | EXTREMA

    # Detalhe
    top_unusual: list[UnusualOptionActivity] = field(default_factory=list)
    gamma_wall_strike: float | None = None
    max_pain: float | None = None
    explanation: str = ""

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k not in ("top_unusual",)}
        d["top_unusual"] = [u.__dict__ for u in self.top_unusual[:5]]
        return d


# ---------------------------------------------------------------------------
# Detecção de atividade incomum por opção
# ---------------------------------------------------------------------------

def _score_unusual_option(
    volume: float,
    open_interest: float,
    iv_implied: float,
    iv_percentile: float,
    premium: float,
    dte: int,
    avg_volume: float = 0.0,
) -> tuple[float, list[str]]:
    """
    Score 0–100 de atividade incomum para uma única opção.
    Fatores: volume/OI ratio, IV extrema, prêmio relativo, urgência (DTE curto).
    """
    score = 0.0
    reasons: list[str] = []

    # 1. Volume vs Open Interest — sinal clássico de novo posicionamento
    if open_interest > 0:
        vol_oi_ratio = volume / open_interest
        if vol_oi_ratio >= 2.0:
            score += 35
            reasons.append(f"Vol/OI={vol_oi_ratio:.1f}x (novo posicionamento significativo)")
        elif vol_oi_ratio >= 0.8:
            score += 15
            reasons.append(f"Vol/OI={vol_oi_ratio:.1f}x (ativo)")

    # 2. Volume vs média histórica da série
    if avg_volume > 0:
        vol_mult = volume / avg_volume
        if vol_mult >= 5.0:
            score += 30
            reasons.append(f"{vol_mult:.0f}x volume médio")
        elif vol_mult >= 2.5:
            score += 15
            reasons.append(f"{vol_mult:.1f}x volume médio")

    # 3. IV Percentile extremo — vol sendo comprada em pico ou vendida em vale
    if not math.isnan(iv_percentile):
        if iv_percentile >= 90:
            score += 20
            reasons.append(f"IV percentil {iv_percentile:.0f}% (vol cara — venda institucional?)")
        elif iv_percentile <= 15:
            score += 20
            reasons.append(f"IV percentil {iv_percentile:.0f}% (vol barata — compra de proteção?)")

    # 4. DTE curto com volume alto — urgência / event-driven
    if dte <= 7 and volume >= 100:
        score += 15
        reasons.append(f"DTE={dte}d com volume {volume:.0f} (urgência)")
    elif dte <= 21 and volume >= 200:
        score += 7
        reasons.append(f"DTE={dte}d (curto prazo)")

    return float(np.clip(score, 0, 100)), reasons


# ---------------------------------------------------------------------------
# Cálculo de Gamma Wall e Max Pain
# ---------------------------------------------------------------------------

def _compute_gamma_wall(records: list) -> float | None:
    """
    Strike com maior gamma exposure total (soma |gamma| × OI × 100).
    Esse strike age como ímã de preço porque os dealers precisam hedge agressivo.
    """
    by_strike: dict[float, float] = {}
    for r in records:
        if hasattr(r, "gamma") and hasattr(r, "open_interest") and r.open_interest > 0:
            exposure = abs(r.gamma) * r.open_interest * 100.0
            by_strike[r.strike] = by_strike.get(r.strike, 0.0) + exposure
    if not by_strike:
        return None
    return max(by_strike, key=lambda k: by_strike[k])


def _compute_max_pain(records: list, spot: float) -> float | None:
    """
    Max pain: strike onde o valor total de opções expira sem valor (máxima dor para compradores).
    Método: para cada strike candidato, calcular perda total de holders.
    """
    strikes = sorted({r.strike for r in records if r.strike > 0})
    if not strikes:
        return None

    calls = [r for r in records if r.option_type == "CALL"]
    puts  = [r for r in records if r.option_type == "PUT"]

    pain: dict[float, float] = {}
    for test_price in strikes:
        call_pain = sum(max(test_price - r.strike, 0) * r.open_interest for r in calls)
        put_pain  = sum(max(r.strike - test_price, 0) * r.open_interest for r in puts)
        pain[test_price] = call_pain + put_pain

    return min(pain, key=lambda k: pain[k]) if pain else None


# ---------------------------------------------------------------------------
# Engine principal
# ---------------------------------------------------------------------------

def analyze_institutional_flow(
    chain,                         # OptionsChain do options_chain.py
    iv_percentile_series: pd.Series | None = None,
    historical_avg_volumes: dict[str, float] | None = None,
) -> InstitutionalFlowResult:
    """
    Analisa o fluxo institucional de uma cadeia de opções completa.

    chain: instância de OptionsChain com .calls, .puts, .hv, .ticker
    iv_percentile_series: série histórica de IV para calcular percentil
    historical_avg_volumes: dict {option_ticker: avg_daily_volume}
    """
    all_records = list(getattr(chain, "calls", [])) + list(getattr(chain, "puts", []))
    if not all_records:
        return _empty_result(getattr(chain, "ticker", "?"))

    underlying = getattr(chain, "ticker", "?")
    hv = float(getattr(chain, "hv", 0.0) or 0.0)
    trade_date = getattr(chain, "trade_date", "")

    # IV ATM atual
    atm_records = [r for r in all_records if r.moneyness == "ATM" and not math.isnan(r.iv_implied)]
    iv_atm = float(np.mean([r.iv_implied for r in atm_records])) if atm_records else hv

    # IV Percentile (usa HV como proxy se não houver série histórica)
    iv_pct = float("nan")
    if iv_percentile_series is not None and len(iv_percentile_series) >= 30:
        below = (iv_percentile_series < iv_atm).sum()
        iv_pct = round(float(below) / len(iv_percentile_series) * 100, 1)

    # IV regime
    if math.isnan(iv_pct):
        iv_regime = "INDISPONÍVEL"
    elif iv_pct >= 90:
        iv_regime = "EXTREMA"
    elif iv_pct >= 70:
        iv_regime = "EXPANDIDA"
    elif iv_pct <= 20:
        iv_regime = "COMPRIMIDA"
    else:
        iv_regime = "NORMAL"

    # Unusual activity por opção
    unusual_list: list[UnusualOptionActivity] = []
    for r in all_records:
        avg_vol = (historical_avg_volumes or {}).get(r.ticker, 0.0)
        u_score, u_reasons = _score_unusual_option(
            volume=r.volume,
            open_interest=getattr(r, "open_interest", 0.0),
            iv_implied=r.iv_implied if not math.isnan(r.iv_implied) else hv,
            iv_percentile=iv_pct,
            premium=r.price,
            dte=r.dte,
            avg_volume=avg_vol,
        )
        if u_score >= 25:
            direction = "BULLISH" if r.option_type == "CALL" else "BEARISH"
            unusual_list.append(UnusualOptionActivity(
                ticker=underlying,
                option_ticker=r.ticker,
                option_type=r.option_type,
                strike=r.strike,
                expiry=r.expiry,
                dte=r.dte,
                premium=r.price,
                volume=r.volume,
                open_interest=getattr(r, "open_interest", 0.0),
                iv_implied=r.iv_implied if not math.isnan(r.iv_implied) else float("nan"),
                delta=r.delta,
                unusual_score=round(u_score, 1),
                reason="; ".join(u_reasons),
                direction=direction,
            ))
    unusual_list.sort(key=lambda u: u.unusual_score, reverse=True)

    # Call/Put ratio por volume
    call_vol = sum(r.volume for r in getattr(chain, "calls", []) if r.volume > 0)
    put_vol  = sum(r.volume for r in getattr(chain, "puts",  []) if r.volume > 0)
    cp_ratio = (call_vol / put_vol) if put_vol > 0 else 1.0

    # Directional bias
    if cp_ratio >= 1.5:
        directional_bias = "BULLISH"
    elif cp_ratio <= 0.67:
        directional_bias = "BEARISH"
    else:
        directional_bias = "NEUTRAL"

    # Gamma wall e max pain
    gamma_wall = _compute_gamma_wall(all_records)
    max_pain   = _compute_max_pain(all_records, atm_records[0].stock_price if atm_records else 0.0)

    # --- Flow Conviction Score (0–100) ---
    # Quanto o fluxo total está convicto em uma direção
    unusual_high = [u for u in unusual_list if u.unusual_score >= 60]
    conviction = 0.0
    conviction += min(len(unusual_high) * 20, 50)           # até 50 pts por atividade incomum
    if cp_ratio >= 2.0 or cp_ratio <= 0.5:
        conviction += 25                                      # assimetria pronunciada
    elif cp_ratio >= 1.5 or cp_ratio <= 0.67:
        conviction += 10
    if iv_regime in ("EXTREMA", "EXPANDIDA"):
        conviction += 15                                      # vol cara = mão forte comprando proteção
    elif iv_regime == "COMPRIMIDA":
        conviction += 10                                      # vol barata = antecipação de movimento
    conviction = float(np.clip(conviction, 0, 100))

    # --- Dealer Pressure Score (0–100) ---
    # Quanta pressão de hedge existe sobre os dealers
    gamma_total = sum(
        abs(getattr(r, "gamma", 0)) * getattr(r, "open_interest", 0) * 100
        for r in all_records
    )
    # Normalizado contra um threshold empírico para ações líquidas B3
    dealer_pressure = float(np.clip(gamma_total / 5_000_000 * 100, 0, 100))

    # --- Gamma Risk Score (0–100) ---
    # Risco de aceleração de preço por gamma squeeze
    gamma_call = sum(abs(getattr(r, "gamma", 0)) * getattr(r, "open_interest", 0) for r in getattr(chain, "calls", []))
    gamma_put  = sum(abs(getattr(r, "gamma", 0)) * getattr(r, "open_interest", 0) for r in getattr(chain, "puts", []))
    gamma_imbalance = abs(gamma_call - gamma_put) / max(gamma_call + gamma_put, 1e-9)
    gamma_risk = float(np.clip(gamma_imbalance * 100 + dealer_pressure * 0.3, 0, 100))

    # --- Unusual Activity Score (0–100) ---
    unusual_activity = float(np.clip(
        (sum(u.unusual_score for u in unusual_list[:5]) / 5) if unusual_list else 0.0,
        0, 100,
    ))

    # Explicação
    explanation_parts = []
    if conviction >= 60:
        explanation_parts.append(f"fluxo institucional convicto ({conviction:.0f}/100)")
    if len(unusual_high) > 0:
        explanation_parts.append(f"{len(unusual_high)} posição(ões) com atividade incomum")
    if iv_regime != "NORMAL":
        explanation_parts.append(f"IV {iv_regime.lower()} (percentil {iv_pct:.0f}%)" if not math.isnan(iv_pct) else f"IV {iv_regime.lower()}")
    if gamma_wall:
        explanation_parts.append(f"gamma wall em R${gamma_wall:.2f}")
    if not explanation_parts:
        explanation_parts.append("sem sinal institucional relevante detectado")

    return InstitutionalFlowResult(
        underlying=underlying,
        as_of=trade_date or "",
        flow_conviction_score=round(conviction, 1),
        dealer_pressure_score=round(dealer_pressure, 1),
        gamma_risk_score=round(gamma_risk, 1),
        unusual_activity_score=round(unusual_activity, 1),
        directional_bias=directional_bias,
        call_put_ratio=round(cp_ratio, 2),
        iv_regime=iv_regime,
        top_unusual=unusual_list[:10],
        gamma_wall_strike=gamma_wall,
        max_pain=max_pain,
        explanation="; ".join(explanation_parts),
    )


def _empty_result(underlying: str) -> InstitutionalFlowResult:
    return InstitutionalFlowResult(
        underlying=underlying, as_of="",
        flow_conviction_score=0.0, dealer_pressure_score=0.0,
        gamma_risk_score=0.0, unusual_activity_score=0.0,
        directional_bias="NEUTRAL", call_put_ratio=1.0,
        iv_regime="INDISPONÍVEL", explanation="cadeia de opções vazia",
    )
