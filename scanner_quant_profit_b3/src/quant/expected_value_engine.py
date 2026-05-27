"""
Expected Value Engine — Probabilidade × Payoff Ajustado por Risco.

Transforma sinais quant em expected value real, incorporando:
  - Probabilidade de acerto histórica da estratégia
  - Payoff potencial (upside capturado)
  - Downside máximo (risco real, não percentual)
  - Assimetria (quanto ganho vs perda em magnitude)
  - Kelly fraction (sizing ótimo implícito)

expected_value_score = f(probabilidade, payoff_ratio, assimetria, convicção)

Não usa LLM. Todos os inputs são numéricos e rastreáveis.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------

@dataclass
class EVResult:
    ticker: str

    # Componentes de EV
    probability_win: float       # 0.0–1.0 (estimativa de acerto)
    expected_payoff: float       # R$ ou % esperado
    payoff_ratio: float          # ganho_médio / perda_média
    asymmetry_score: float       # 0–100 (quão assimétrico favorável)

    # Scores derivados
    expected_value_score: float  # 0–100 (qualidade EV normalizada)
    kelly_fraction: float        # fração ótima implícita (0–0.5 clampado)
    downside_asymmetry: bool     # True se payoff_ratio < 1 (risco > ganho)

    # Contexto
    max_upside_pct: float
    max_drawdown_pct: float
    conviction_level: str        # FORTE | MODERADO | FRACO | INSUFICIENTE
    explanation: str


# ---------------------------------------------------------------------------
# Primitivas matemáticas
# ---------------------------------------------------------------------------

def kelly_fraction(p_win: float, payoff_ratio: float) -> float:
    """
    Kelly ótimo: f = p - (1-p)/b  onde b = payoff_ratio.
    Retorna fração positiva ou 0 (sem apostar se EV negativo).
    Clampado em 0.5 (half-Kelly como teto de prudência).
    """
    if payoff_ratio <= 0:
        return 0.0
    f = p_win - (1.0 - p_win) / payoff_ratio
    return float(np.clip(f, 0.0, 0.50))


def _asymmetry_score(payoff_ratio: float) -> float:
    """
    Score 0–100 de assimetria favorável.
    payoff_ratio=1 → score 30 (neutro)
    payoff_ratio=3 → score 90 (excelente)
    payoff_ratio=0.5 → score 10 (desfavorável)
    """
    if payoff_ratio <= 0:
        return 0.0
    # log scale: ln(3)≈1.1 → score 100
    raw = 30.0 + 40.0 * math.log(max(payoff_ratio, 0.01))
    return float(np.clip(raw, 0, 100))


def _ev_score_normalized(
    p_win: float,
    payoff_ratio: float,
    conviction_multiplier: float = 1.0,
) -> float:
    """
    Score normalizado 0–100 baseado em EV e assimetria.
    Penaliza p_win muito baixo mesmo com payoff alto (fragmentação de tese).
    """
    if p_win <= 0 or payoff_ratio <= 0:
        return 0.0

    # EV base em unidades de risco
    ev_units = p_win * payoff_ratio - (1.0 - p_win)

    # Escala: EV=0 → score=30, EV=1→score=80, EV=2→score=100
    ev_score = 30.0 + ev_units * 35.0

    # Bônus de assimetria
    asym = _asymmetry_score(payoff_ratio)
    final = ev_score * 0.70 + asym * 0.30

    return float(np.clip(final * conviction_multiplier, 0, 100))


# ---------------------------------------------------------------------------
# Engine principal
# ---------------------------------------------------------------------------

def compute_ev(
    ticker: str,
    *,
    probability_win: float,
    max_upside_pct: float,
    max_drawdown_pct: float,
    conviction_score: float = 50.0,    # 0–100, de outro layer (quant/flow)
    historical_hit_rate: float | None = None,  # de backtest se disponível
) -> EVResult:
    """
    Calcula o expected value score de uma oportunidade.

    probability_win   : estimativa direta ou derivada de backtests [0.0–1.0]
    max_upside_pct    : retorno positivo esperado (ex: 8.0 para 8%)
    max_drawdown_pct  : perda máxima esperada (ex: 5.0 para -5%, passar positivo)
    conviction_score  : score de convicção de outro módulo [0–100]
    historical_hit_rate: taxa de acerto histórico de backtests (override se disponível)
    """
    # Ajuste de probabilidade: backtest > estimativa direta
    p = historical_hit_rate if historical_hit_rate is not None else probability_win
    p = float(np.clip(p, 0.01, 0.99))

    upside  = abs(max_upside_pct)
    down    = abs(max_drawdown_pct) if max_drawdown_pct != 0 else 1.0

    payoff_ratio = upside / down if down > 0 else float("nan")
    if math.isnan(payoff_ratio) or payoff_ratio <= 0:
        return _invalid_result(ticker, "payoff_ratio inválido (drawdown=0?)")

    expected_payoff = p * upside - (1.0 - p) * down
    asym = _asymmetry_score(payoff_ratio)
    conviction_multiplier = 0.5 + conviction_score / 200.0   # 0.5–1.0

    ev_score = _ev_score_normalized(p, payoff_ratio, conviction_multiplier)
    kf = kelly_fraction(p, payoff_ratio)
    downside_asym = payoff_ratio < 1.0

    # Conviction level
    if ev_score >= 70 and p >= 0.55:
        conv = "FORTE"
    elif ev_score >= 50 and p >= 0.48:
        conv = "MODERADO"
    elif ev_score >= 30:
        conv = "FRACO"
    else:
        conv = "INSUFICIENTE"

    # Explicação
    parts = []
    parts.append(f"P(acerto)={p:.0%}, payoff={payoff_ratio:.1f}:1")
    if payoff_ratio >= 2.0:
        parts.append(f"assimetria favorável ({payoff_ratio:.1f}x upside vs downside)")
    elif downside_asym:
        parts.append(f"risco supera ganho ({payoff_ratio:.2f}:1) — cautela")
    if kf >= 0.10:
        parts.append(f"Kelly={kf:.0%} (suporte para sizing)")
    if expected_payoff >= 2.0:
        parts.append(f"EV={expected_payoff:+.1f}% (positivo)")
    elif expected_payoff < 0:
        parts.append(f"EV={expected_payoff:+.1f}% (negativo — reconsiderar)")

    return EVResult(
        ticker=ticker,
        probability_win=round(p, 3),
        expected_payoff=round(expected_payoff, 2),
        payoff_ratio=round(payoff_ratio, 2),
        asymmetry_score=round(asym, 1),
        expected_value_score=round(ev_score, 1),
        kelly_fraction=round(kf, 3),
        downside_asymmetry=downside_asym,
        max_upside_pct=round(upside, 2),
        max_drawdown_pct=round(down, 2),
        conviction_level=conv,
        explanation="; ".join(parts),
    )


def _invalid_result(ticker: str, reason: str) -> EVResult:
    return EVResult(
        ticker=ticker, probability_win=0.0, expected_payoff=0.0,
        payoff_ratio=0.0, asymmetry_score=0.0, expected_value_score=0.0,
        kelly_fraction=0.0, downside_asymmetry=True,
        max_upside_pct=0.0, max_drawdown_pct=0.0,
        conviction_level="INSUFICIENTE", explanation=reason,
    )


# ---------------------------------------------------------------------------
# Ranking probabilístico de oportunidades
# ---------------------------------------------------------------------------

def rank_by_ev(
    opportunities: list[dict[str, Any]],
    *,
    min_ev_score: float = 35.0,
    min_probability: float = 0.45,
    min_payoff_ratio: float = 0.8,
) -> list[dict[str, Any]]:
    """
    Ranqueia oportunidades por expected_value_score aplicando filtros mínimos.

    Cada item em `opportunities` deve conter:
        ticker, probability_win, max_upside_pct, max_drawdown_pct
        e opcionalmente: conviction_score, historical_hit_rate

    Retorna lista ordenada decrescente com EVResult embutido em 'ev'.
    """
    results = []
    for opp in opportunities:
        ticker = opp.get("ticker", "?")
        try:
            ev = compute_ev(
                ticker,
                probability_win=float(opp.get("probability_win", 0.5)),
                max_upside_pct=float(opp.get("max_upside_pct", 5.0)),
                max_drawdown_pct=float(opp.get("max_drawdown_pct", 3.0)),
                conviction_score=float(opp.get("conviction_score", 50.0)),
                historical_hit_rate=opp.get("historical_hit_rate"),
            )
        except Exception:
            continue

        if ev.expected_value_score < min_ev_score:
            continue
        if ev.probability_win < min_probability:
            continue
        if ev.payoff_ratio < min_payoff_ratio:
            continue

        results.append({**opp, "ev": ev.to_dict() if hasattr(ev, "to_dict") else ev.__dict__})

    results.sort(key=lambda x: x["ev"]["expected_value_score"], reverse=True)
    return results
