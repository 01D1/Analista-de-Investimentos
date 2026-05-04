"""
Matemática de opções: Black-Scholes, Greeks, moneyness, liquidez.
Adaptado para o mercado brasileiro (B3) com taxa SELIC como livre de risco.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from datetime import date
from typing import Literal


# ---------------------------------------------------------------------------
# Resultado consolidado de um cálculo BS
# ---------------------------------------------------------------------------

@dataclass
class OptionResult:
    price: float
    delta: float
    gamma: float
    theta: float          # por dia calendário
    vega: float           # por 1pp de vol (input sigma em decimal)
    rho: float            # por 1pp de taxa
    moneyness: Literal["ITM", "ATM", "OTM"]
    moneyness_pct: float  # (S/K - 1) * 100  para CALL; (K/S - 1)*100 para PUT
    intrinsic_value: float
    time_value: float


# ---------------------------------------------------------------------------
# Black-Scholes
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    from math import erfc, sqrt
    return 0.5 * erfc(-x / sqrt(2))


def _norm_pdf(x: float) -> float:
    return np.exp(-0.5 * x ** 2) / np.sqrt(2 * np.pi)


def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "CALL",
) -> OptionResult:
    """
    Modelo Black-Scholes para opções europeias.

    Args:
        S:           preço spot do ativo objeto
        K:           preço de exercício (strike)
        T:           tempo até o vencimento em ANOS (ex: 30 dias = 30/365)
        r:           taxa livre de risco anualizada (ex: 0.1475 para SELIC 14.75%)
        sigma:       volatilidade implícita/histórica anualizada (ex: 0.30 = 30%)
        option_type: "CALL" ou "PUT"
    """
    otype = option_type.upper()

    # Degeneração: opção vencida ou parâmetros inválidos
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        intrinsic = max(S - K, 0.0) if otype == "CALL" else max(K - S, 0.0)
        return OptionResult(
            price=intrinsic,
            delta=1.0 if (otype == "CALL" and S > K) else (0.0 if otype == "CALL" else -1.0),
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            rho=0.0,
            moneyness=_classify_moneyness(S, K, otype),
            moneyness_pct=_moneyness_pct(S, K, otype),
            intrinsic_value=intrinsic,
            time_value=0.0,
        )

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    # ---- preço ----
    if otype == "CALL":
        price = S * _norm_cdf(d1) - K * np.exp(-r * T) * _norm_cdf(d2)
        intrinsic = max(S - K, 0.0)
        delta = _norm_cdf(d1)
        rho = K * T * np.exp(-r * T) * _norm_cdf(d2) / 100.0
    else:
        price = K * np.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        intrinsic = max(K - S, 0.0)
        delta = _norm_cdf(d1) - 1.0
        rho = -K * T * np.exp(-r * T) * _norm_cdf(-d2) / 100.0

    # ---- Greeks ----
    pdf_d1 = _norm_pdf(d1)
    gamma = pdf_d1 / (S * sigma * sqrt_T)
    # Theta por dia calendário
    theta = (
        -(S * pdf_d1 * sigma) / (2.0 * sqrt_T)
        - r * K * np.exp(-r * T) * _norm_cdf(d2 if otype == "CALL" else -d2)
        * (1.0 if otype == "CALL" else -1.0)
    ) / 365.0
    vega = S * pdf_d1 * sqrt_T / 100.0  # por 1pp de vol

    time_value = max(price - intrinsic, 0.0)

    return OptionResult(
        price=round(price, 4),
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        theta=round(theta, 4),
        vega=round(vega, 4),
        rho=round(rho, 4),
        moneyness=_classify_moneyness(S, K, otype),
        moneyness_pct=round(_moneyness_pct(S, K, otype), 2),
        intrinsic_value=round(intrinsic, 4),
        time_value=round(time_value, 4),
    )


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _moneyness_pct(S: float, K: float, otype: str) -> float:
    if K == 0:
        return 0.0
    if otype == "CALL":
        return (S / K - 1.0) * 100.0
    else:
        return (K / S - 1.0) * 100.0 if S > 0 else 0.0


def _classify_moneyness(S: float, K: float, otype: str, band_pct: float = 2.0) -> str:
    if K == 0 or S == 0:
        return "ATM"
    diff = (S - K) / K * 100.0
    if abs(diff) <= band_pct:
        return "ATM"
    if otype == "CALL":
        return "ITM" if S > K else "OTM"
    else:
        return "ITM" if S < K else "OTM"


def days_to_expiration(trade_date, expiration_date) -> int:
    """
    Retorna o número de dias corridos entre trade_date e expiration_date.
    Aceita objetos date ou strings ISO 8601.
    """
    from dateutil.parser import parse as _parse

    def _to_date(v):
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if hasattr(v, "date"):
            return v.date()
        s = str(v).strip()
        # Formato YYYYMMDD sem separadores (ex: B3 option_maturity)
        if len(s) == 8 and s.isdigit():
            try:
                from datetime import date as _date
                return _date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except Exception:
                pass
        try:
            return _parse(s).date()
        except Exception:
            return None

    t = _to_date(trade_date)
    e = _to_date(expiration_date)
    if t is None or e is None:
        return 0
    return max((e - t).days, 0)


def estimated_spread(option_price: float, volume: float, trades: int) -> float:
    """
    Proxy de spread bid-ask a partir de dados de fechamento.
    Quanto maior o retorno, mais caro é negociar.
    """
    if option_price <= 0:
        return float("inf")
    if trades <= 0 or volume <= 0:
        return option_price * 0.10  # 10% por padrão se sem liquidez

    avg_size = volume / trades / option_price
    # Fórmula heurística: spread proporcional ao inverso do tamanho médio
    spread = max(0.01, 0.05 / max(avg_size, 0.1)) * option_price
    return round(min(spread, option_price * 0.15), 4)


def liquidity_score(
    trades: int,
    volume: float,
    min_trades: int,
    min_volume: float,
) -> float:
    """
    Score 0–100 de liquidez da opção.
    50% peso para negócios, 50% para volume financeiro.
    """
    t_score = min(1.0, trades / max(min_trades, 1)) * 50.0
    v_score = min(1.0, volume / max(min_volume, 1)) * 50.0
    return round(t_score + v_score, 2)
