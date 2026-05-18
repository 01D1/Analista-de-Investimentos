"""Risco de portfolio."""
from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_correlation_matrix(returns_df: pd.DataFrame):
    return returns_df.apply(pd.to_numeric, errors="coerce").corr()


def calculate_covariance_matrix(returns_df: pd.DataFrame):
    return returns_df.apply(pd.to_numeric, errors="coerce").cov()


def calculate_portfolio_volatility(weights, covariance_matrix):
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(covariance_matrix, dtype=float)
    if w.size == 0 or cov.size == 0:
        return np.nan
    return float(np.sqrt(w.T @ cov @ w))


def calculate_portfolio_drawdown(equity_curve):
    curve = pd.to_numeric(pd.Series(equity_curve), errors="coerce").dropna()
    if curve.empty:
        return {"max_drawdown": np.nan, "drawdown_series": pd.Series(dtype=float)}
    dd = curve / curve.cummax() - 1
    return {"max_drawdown": float(dd.min()), "drawdown_series": dd}


def calculate_risk_concentration(weights):
    w = pd.to_numeric(pd.Series(weights), errors="coerce").dropna().abs()
    if w.empty:
        return {"top_concentration": np.nan, "hhi": np.nan}
    total = w.sum()
    norm = w / total if total else w
    return {"top_concentration": float(norm.max()), "hhi": float((norm**2).sum())}


def calculate_asset_risk_contribution(weights, covariance_matrix):
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(covariance_matrix, dtype=float)
    vol = calculate_portfolio_volatility(w, cov)
    if not vol or pd.isna(vol):
        return []
    mrc = cov @ w / vol
    rc = w * mrc
    total = rc.sum()
    return (rc / total).tolist() if total else rc.tolist()

