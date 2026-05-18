"""Modelos de Value at Risk."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


Z = {0.95: 1.65, 0.99: 2.33}


def _z(confidence: float) -> float:
    return Z.get(round(float(confidence), 2), 1.65)


def _daily_vol(volatility: float) -> float:
    if volatility is None or pd.isna(volatility):
        return np.nan
    return float(volatility) / math.sqrt(252) if float(volatility) > 0.10 else float(volatility)


def calculate_parametric_var(position_value, volatility, confidence: float = 0.95, horizon_days: int = 1) -> dict:
    if position_value is None or volatility is None or pd.isna(volatility) or float(position_value) <= 0:
        return {"parametric_var": np.nan, "confidence": confidence, "horizon_days": horizon_days, "diagnostic_message": "Dados insuficientes para VaR parametrico."}
    var = float(position_value) * _daily_vol(float(volatility)) * _z(confidence) * math.sqrt(horizon_days)
    return {"parametric_var": round(abs(var), 6), "confidence": confidence, "horizon_days": horizon_days, "diagnostic_message": "OK"}


def calculate_historical_var(returns, position_value, confidence: float = 0.95) -> dict:
    r = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if len(r) < 20 or float(position_value or 0) <= 0:
        return {"historical_var": np.nan, "confidence": confidence, "diagnostic_message": "Dados insuficientes para VaR historico."}
    q = r.quantile(1 - confidence)
    return {"historical_var": round(abs(float(position_value) * float(q)), 6), "confidence": confidence, "diagnostic_message": "OK"}


def calculate_modified_var(returns, position_value, confidence: float = 0.95) -> dict:
    r = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if len(r) < 30 or float(position_value or 0) <= 0:
        return {"modified_var": np.nan, "confidence": confidence, "diagnostic_message": "Dados insuficientes para VaR modificado."}
    z = _z(confidence)
    skew = r.skew()
    kurt = r.kurt()
    z_cf = z + (z**2 - 1) * skew / 6 + (z**3 - 3 * z) * kurt / 24 - (2 * z**3 - 5 * z) * skew**2 / 36
    sigma = r.std()
    return {"modified_var": round(abs(float(position_value) * sigma * z_cf), 6), "confidence": confidence, "diagnostic_message": "OK"}


def calculate_portfolio_var(weights, covariance_matrix, portfolio_value, confidence: float = 0.95) -> dict:
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(covariance_matrix, dtype=float)
    if w.size == 0 or cov.size == 0 or portfolio_value <= 0:
        return {"portfolio_var": np.nan, "diagnostic_message": "Dados insuficientes para VaR de portfolio."}
    vol = math.sqrt(float(w.T @ cov @ w))
    return {"portfolio_var": round(abs(portfolio_value * vol * _z(confidence)), 6), "portfolio_vol": vol, "confidence": confidence, "diagnostic_message": "OK"}


def calculate_component_var(weights, covariance_matrix, portfolio_value, confidence: float = 0.95) -> dict:
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(covariance_matrix, dtype=float)
    if w.size == 0 or cov.size == 0:
        return {"component_var": [], "diagnostic_message": "Dados insuficientes para Component VaR."}
    port_vol = math.sqrt(float(w.T @ cov @ w))
    if port_vol == 0:
        return {"component_var": [0.0] * len(w), "diagnostic_message": "Volatilidade nula."}
    marginal = cov @ w / port_vol
    comp = w * marginal * portfolio_value * _z(confidence)
    return {"component_var": comp.tolist(), "diagnostic_message": "OK"}

