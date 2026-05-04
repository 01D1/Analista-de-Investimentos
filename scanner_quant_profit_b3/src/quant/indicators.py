"""
Indicadores técnicos para análise quantitativa.
Todos os indicadores operam sobre pd.Series e retornam pd.Series.
"""
import numpy as np
import pandas as pd


def log_returns(prices: pd.Series) -> pd.Series:
    """Retornos logarítmicos: ln(P_t / P_{t-1})."""
    return np.log(prices / prices.shift(1))


def sma(prices: pd.Series, window: int) -> pd.Series:
    """Média Móvel Simples."""
    return prices.rolling(window=window, min_periods=1).mean()


def ema(prices: pd.Series, span: int) -> pd.Series:
    """Média Móvel Exponencial (EWM)."""
    return prices.ewm(span=span, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — mede volatilidade intraday."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (0-100). Retorna 100 quando não há perdas, 0 quando não há ganhos."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_vals = 100.0 - (100.0 / (1.0 + rs))
    # Sem perdas → RSI=100; sem ganhos → RSI=0
    rsi_vals = rsi_vals.where(avg_loss > 0, other=100.0)
    rsi_vals = rsi_vals.where(avg_gain > 0, other=0.0)
    return rsi_vals


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD line, Signal line, Histogram.
    Retorna (macd_line, signal_line, histogram).
    """
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def vwap(prices: pd.Series, volumes: pd.Series) -> pd.Series:
    """
    Volume Weighted Average Price (VWAP).
    Para uso intraday: reinicialize os arrays a cada sessão.
    """
    cum_vol = volumes.cumsum()
    cum_pv = (prices * volumes).cumsum()
    return cum_pv / cum_vol.replace(0, np.nan)


def zscore(series: pd.Series, window: int = 20) -> pd.Series:
    """Z-score rolante: quantos desvios padrão acima/abaixo da média."""
    mean = series.rolling(window=window, min_periods=2).mean()
    std = series.rolling(window=window, min_periods=2).std()
    return (series - mean) / std.replace(0, np.nan)


def bollinger_bands(
    prices: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bandas de Bollinger.
    Retorna (upper, middle, lower).
    """
    middle = sma(prices, window)
    std = prices.rolling(window=window, min_periods=2).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower
