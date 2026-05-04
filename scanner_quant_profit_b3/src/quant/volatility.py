"""
Modelos de volatilidade para análise de opções e risco.
"""
import numpy as np
import pandas as pd

from .indicators import log_returns


def historical_volatility(
    prices: pd.Series,
    window: int = 21,
    annualize: bool = True,
    trading_days: int = 252,
) -> pd.Series:
    """
    Volatilidade histórica anualizada.
    Usa janela rolante de retornos logarítmicos.
    """
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
    """Volatilidade realizada (escalar) de uma série de retornos."""
    rv = float(returns.std())
    if annualize:
        rv *= np.sqrt(trading_days)
    return rv


def volatility_zscore(
    prices: pd.Series,
    window: int = 21,
    lookback: int = 252,
) -> float:
    """
    Z-score da volatilidade atual vs histórico.
    Positivo = vol acima da média histórica (regime de medo).
    Negativo = vol abaixo da média (regime de complacência).
    """
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
    Volatility cone: percentis da vol histórica em diferentes janelas.
    Útil para contextualizar se a vol atual está cara ou barata.
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
