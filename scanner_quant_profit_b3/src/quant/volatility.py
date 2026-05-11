"""
Modelos de volatilidade: HV, IV surface, smile, cone, z-score.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from .indicators import log_returns


# ---------------------------------------------------------------------------
# Volatilidade Histórica
# ---------------------------------------------------------------------------

def historical_volatility(
    prices: pd.Series,
    window: int = 21,
    annualize: bool = True,
    trading_days: int = 252,
) -> pd.Series:
    """HV anualizada por janela rolante de retornos logarítmicos."""
    rets = log_returns(prices)
    hv = rets.rolling(window=window, min_periods=max(window // 2, 2)).std()
    if annualize:
        hv = hv * np.sqrt(trading_days)
    return hv


def realized_volatility(
    returns: pd.Series,
    annualize: bool = True,
    trading_days: int = 252,
) -> float:
    rv = float(returns.std())
    if annualize:
        rv *= np.sqrt(trading_days)
    return rv


def volatility_zscore(
    prices: pd.Series,
    window: int = 21,
    lookback: int = 252,
) -> float:
    """Z-score da vol atual vs histórico. Positivo = regime de medo."""
    hv = historical_volatility(prices, window=window)
    recent = hv.iloc[-1]
    hist = hv.iloc[-lookback:].dropna()
    if len(hist) < 10 or hist.std() == 0:
        return 0.0
    return float((recent - hist.mean()) / hist.std())


def volatility_cone(
    prices: pd.Series,
    windows: list[int] | None = None,
    quantiles: list[float] | None = None,
) -> pd.DataFrame:
    """
    Volatility cone: percentis da HV em diferentes janelas.
    Útil para identificar se a vol atual está cara ou barata.
    """
    if windows is None:
        windows = [10, 21, 42, 63]
    if quantiles is None:
        quantiles = [0.10, 0.25, 0.50, 0.75, 0.90]

    rows = []
    for w in windows:
        hv = historical_volatility(prices, window=w).dropna()
        row = {"window": w, "current": hv.iloc[-1] if not hv.empty else np.nan}
        for q in quantiles:
            row[f"p{int(q * 100)}"] = hv.quantile(q)
        rows.append(row)
    return pd.DataFrame(rows).set_index("window")


# ---------------------------------------------------------------------------
# Superfície de Volatilidade Implícita
# ---------------------------------------------------------------------------

def build_vol_surface(
    options_records: list,
    min_liq_score: float = 20.0,
) -> pd.DataFrame:
    """
    Monta a superfície IV × Strike × Vencimento a partir de OptionRecords.

    Retorna DataFrame pivotado:
        index   = strike (absoluto)
        columns = expiry (YYYYMMDD)
        values  = iv_implied (decimal, ex: 0.32 = 32%)

    Só inclui registros com iv_implied válida (não-NaN) e liq_score >= min_liq_score.
    """
    rows = []
    for r in options_records:
        iv = getattr(r, "iv_implied", float("nan"))
        if math.isnan(iv) or iv <= 0:
            continue
        if getattr(r, "liq_score", 0) < min_liq_score:
            continue
        rows.append({
            "strike": r.strike,
            "expiry": r.expiry,
            "dte":    r.dte,
            "iv":     iv,
            "opt_type": r.option_type,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Média de CALL e PUT para cada strike/vencimento (put-call parity)
    pivot = (
        df.groupby(["strike", "expiry"])["iv"]
        .mean()
        .reset_index()
        .pivot(index="strike", columns="expiry", values="iv")
    )
    pivot.columns.name = None
    return pivot.sort_index()


def iv_smile(
    options_records: list,
    expiry: str,
    opt_type: str = "CALL",
    min_liq_score: float = 20.0,
) -> pd.DataFrame:
    """
    IV smile para um vencimento específico.

    Returns DataFrame com colunas:
        strike, moneyness_pct, iv_implied, delta, liq_score
    ordenado por strike.
    """
    rows = []
    for r in options_records:
        if r.expiry != expiry:
            continue
        if r.option_type.upper() != opt_type.upper():
            continue
        iv = getattr(r, "iv_implied", float("nan"))
        if math.isnan(iv) or iv <= 0:
            continue
        if getattr(r, "liq_score", 0) < min_liq_score:
            continue
        rows.append({
            "ticker":        r.ticker,
            "strike":        r.strike,
            "moneyness_pct": r.moneyness_pct,
            "iv_implied":    iv,
            "iv_hv_spread":  getattr(r, "iv_vs_hv", float("nan")),
            "delta":         r.delta,
            "theta":         r.theta,
            "vega":          r.vega,
            "vanna":         getattr(r, "vanna", 0.0),
            "charm":         getattr(r, "charm", 0.0),
            "vomma":         getattr(r, "vomma", 0.0),
            "liq_score":     r.liq_score,
            "price":         r.price,
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)


def vol_term_structure(
    options_records: list,
    opt_type: str = "CALL",
    moneyness_band: float = 3.0,
    min_liq_score: float = 20.0,
) -> pd.DataFrame:
    """
    Estrutura a termo da IV: IV ATM vs DTE para cada vencimento.

    Returns DataFrame: dte, expiry, iv_atm
    """
    rows = []
    for r in options_records:
        if r.option_type.upper() != opt_type.upper():
            continue
        if abs(r.moneyness_pct) > moneyness_band:
            continue
        iv = getattr(r, "iv_implied", float("nan"))
        if math.isnan(iv) or iv <= 0:
            continue
        if getattr(r, "liq_score", 0) < min_liq_score:
            continue
        rows.append({"dte": r.dte, "expiry": r.expiry, "iv_atm": iv})

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .groupby(["dte", "expiry"])["iv_atm"]
        .mean()
        .reset_index()
        .sort_values("dte")
    )
