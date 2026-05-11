"""
Matemática de opções: Black-Scholes, Greeks completos, IV implícita (Newton-Raphson).
Adaptado para o mercado brasileiro (B3) com taxa SELIC como livre de risco.
"""
from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Resultado consolidado de um cálculo BS
# ---------------------------------------------------------------------------

@dataclass
class OptionResult:
    # Preço
    price: float
    intrinsic_value: float
    time_value: float

    # Greeks de 1ª ordem
    delta: float          # dV/dS
    rho: float            # dV/dr  (por 1pp de taxa)

    # Greeks de 2ª ordem
    gamma: float          # d²V/dS²
    theta: float          # dV/dT  (por dia calendário, negativo = decay)
    vega: float           # dV/dσ  (por 1pp de vol)
    vanna: float          # d²V/dSdσ  = dDelta/dσ
    charm: float          # d²V/dSdT  = dDelta/dT (por dia)

    # Greeks de 3ª ordem
    vomma: float          # d²V/dσ²   = dVega/dσ  (convexidade de vol)
    speed: float          # d³V/dS³   = dGamma/dS

    # Classificação
    moneyness: Literal["ITM", "ATM", "OTM"]
    moneyness_pct: float  # (S/K - 1)*100 CALL; (K/S - 1)*100 PUT


# ---------------------------------------------------------------------------
# Núcleo estatístico
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _moneyness_pct(S: float, K: float, otype: str) -> float:
    if K <= 0 or S <= 0:
        return 0.0
    return (S / K - 1.0) * 100.0 if otype == "CALL" else (K / S - 1.0) * 100.0


def _classify_moneyness(S: float, K: float, otype: str, band: float = 2.0) -> str:
    if K <= 0 or S <= 0:
        return "ATM"
    diff = (S - K) / K * 100.0
    if abs(diff) <= band:
        return "ATM"
    if otype == "CALL":
        return "ITM" if S > K else "OTM"
    return "ITM" if S < K else "OTM"


# ---------------------------------------------------------------------------
# Black-Scholes completo (1ª, 2ª e 3ª ordem)
# ---------------------------------------------------------------------------

def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "CALL",
) -> OptionResult:
    """
    Modelo Black-Scholes para opções europeias com Greeks completos.

    Args:
        S     : preço spot
        K     : strike
        T     : tempo até vencimento em ANOS (ex: 30/365)
        r     : taxa livre de risco anualizada (ex: 0.1475)
        sigma : volatilidade anualizada (ex: 0.30)
        option_type: "CALL" ou "PUT"
    """
    otype = option_type.upper()
    intrinsic = max(S - K, 0.0) if otype == "CALL" else max(K - S, 0.0)

    if T <= 1e-9 or sigma <= 1e-9 or S <= 0 or K <= 0:
        return OptionResult(
            price=intrinsic, intrinsic_value=intrinsic, time_value=0.0,
            delta=1.0 if (otype == "CALL" and S > K) else (-1.0 if (otype == "PUT" and S < K) else 0.0),
            rho=0.0, gamma=0.0, theta=0.0, vega=0.0,
            vanna=0.0, charm=0.0, vomma=0.0, speed=0.0,
            moneyness=_classify_moneyness(S, K, otype),
            moneyness_pct=_moneyness_pct(S, K, otype),
        )

    sqrt_T  = math.sqrt(T)
    d1      = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2      = d1 - sigma * sqrt_T
    pdf_d1  = _norm_pdf(d1)
    disc    = math.exp(-r * T)

    if otype == "CALL":
        price = S * _norm_cdf(d1) - K * disc * _norm_cdf(d2)
        delta = _norm_cdf(d1)
        rho   = K * T * disc * _norm_cdf(d2) / 100.0
        theta_rate = (
            -(S * pdf_d1 * sigma) / (2.0 * sqrt_T)
            - r * K * disc * _norm_cdf(d2)
        ) / 365.0
    else:
        price = K * disc * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1.0
        rho   = -K * T * disc * _norm_cdf(-d2) / 100.0
        theta_rate = (
            -(S * pdf_d1 * sigma) / (2.0 * sqrt_T)
            + r * K * disc * _norm_cdf(-d2)
        ) / 365.0

    # 2ª ordem
    gamma = pdf_d1 / (S * sigma * sqrt_T)
    vega  = S * pdf_d1 * sqrt_T / 100.0       # por 1pp de vol

    # Vanna = dDelta/dσ = -d2/σ * φ(d1)
    vanna = -pdf_d1 * d2 / sigma

    # Charm = dDelta/dT (por dia); sinal indica erosão do delta
    charm = (
        -pdf_d1 * (2.0 * r * T - d2 * sigma * sqrt_T) / (2.0 * T * sigma * sqrt_T)
    ) / 365.0

    # 3ª ordem
    vomma = vega * 100.0 * d1 * d2 / sigma    # dVega/dσ
    speed = -gamma / S * (1.0 + d1 / (sigma * sqrt_T))

    time_val = max(price - intrinsic, 0.0)

    return OptionResult(
        price=round(price, 6),
        intrinsic_value=round(intrinsic, 6),
        time_value=round(time_val, 6),
        delta=round(delta, 6),
        rho=round(rho, 6),
        gamma=round(gamma, 8),
        theta=round(theta_rate, 6),
        vega=round(vega, 6),
        vanna=round(vanna, 6),
        charm=round(charm, 8),
        vomma=round(vomma, 6),
        speed=round(speed, 8),
        moneyness=_classify_moneyness(S, K, otype),
        moneyness_pct=round(_moneyness_pct(S, K, otype), 4),
    )


# ---------------------------------------------------------------------------
# Volatilidade Implícita — Newton-Raphson com fallback bisseção
# ---------------------------------------------------------------------------

def _iv_initial_guess(S: float, K: float, T: float, r: float,
                      market_price: float, otype: str) -> float:
    """Aproximação de Brenner-Subrahmanyam para chute inicial."""
    F = S * math.exp(r * T)
    if F <= 0 or T <= 0:
        return 0.30
    # Corrado-Miller approximation
    try:
        m = market_price - max(S - K * math.exp(-r * T), 0.0) \
            if otype == "CALL" else market_price - max(K * math.exp(-r * T) - S, 0.0)
        m = max(m, 1e-10)
        a = math.sqrt(2 * math.pi / T)
        b = m - (F - K * math.exp(-r * T)) / 2.0
        c = (m - (F - K * math.exp(-r * T)) / 2.0) ** 2
        d = (F - K * math.exp(-r * T)) ** 2 / math.pi
        sq = max(c - d, 0.0)
        sigma = a * (b + math.sqrt(sq)) / (S + K * math.exp(-r * T))
        return max(min(sigma, 5.0), 0.01)
    except Exception:
        return 0.30


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "CALL",
    tol: float = 1e-7,
    max_iter: int = 200,
) -> float:
    """
    Volatilidade Implícita via Newton-Raphson com fallback para bissecção.

    Inverte Black-Scholes: encontra σ tal que BS(S,K,T,r,σ) = market_price.

    Returns:
        IV anualizada (ex: 0.32 = 32%) ou float('nan') se não convergir.
    """
    otype = option_type.upper()

    # Preço de mercado deve ser maior que valor intrínseco
    intrinsic = max(S - K, 0.0) if otype == "CALL" else max(K - S, 0.0)
    if market_price < intrinsic - 1e-6 or market_price <= 0 or T <= 0:
        return float("nan")

    sigma = _iv_initial_guess(S, K, T, r, market_price, otype)

    # ── Newton-Raphson ──────────────────────────────────────────────────────
    for _ in range(max_iter):
        bs   = black_scholes(S, K, T, r, sigma, otype)
        diff = bs.price - market_price
        if abs(diff) < tol:
            return round(sigma, 8)
        # vega em unidades absolutas (bs.vega é por 1pp, então × 100)
        vega_abs = bs.vega * 100.0
        if abs(vega_abs) < 1e-12:
            break   # degenerado — cai para bissecção
        sigma -= diff / vega_abs
        if sigma <= 0:
            sigma = 1e-6

    # ── Fallback: bissecção em [lo, hi] ────────────────────────────────────
    lo, hi = 1e-4, 10.0
    for _ in range(200):
        mid  = (lo + hi) / 2.0
        diff = black_scholes(S, K, T, r, mid, otype).price - market_price
        if abs(diff) < tol:
            return round(mid, 8)
        if diff > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-9:
            return round(mid, 8)

    return float("nan")


# ---------------------------------------------------------------------------
# Auxiliares públicos
# ---------------------------------------------------------------------------

def days_to_expiration(trade_date, expiration_date) -> int:
    from dateutil.parser import parse as _parse

    def _to_date(v):
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if hasattr(v, "date"):
            return v.date()
        s = str(v).strip()
        if len(s) == 8 and s.isdigit():
            try:
                from datetime import date as _d
                return _d(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except Exception:
                pass
        try:
            return _parse(s).date()
        except Exception:
            return None

    t, e = _to_date(trade_date), _to_date(expiration_date)
    if t is None or e is None:
        return 0
    return max((e - t).days, 0)


def estimated_spread(option_price: float, volume: float, trades: int) -> float:
    """Proxy heurístico de spread bid-ask a partir de dados de fechamento."""
    if option_price <= 0:
        return float("inf")
    if trades <= 0 or volume <= 0:
        return option_price * 0.10
    avg_size = volume / trades / option_price
    spread = max(0.01, 0.05 / max(avg_size, 0.1)) * option_price
    return round(min(spread, option_price * 0.15), 4)


def liquidity_score(
    trades: int,
    volume: float,
    min_trades: int,
    min_volume: float,
) -> float:
    """Score 0–100 de liquidez (50% negócios + 50% volume)."""
    t_score = min(1.0, trades / max(min_trades, 1)) * 50.0
    v_score = min(1.0, volume / max(min_volume, 1)) * 50.0
    return round(t_score + v_score, 2)
