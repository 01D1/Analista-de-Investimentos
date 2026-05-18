"""Expected Shortfall / Conditional VaR."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from src.risk.var_models import _daily_vol, _z


def _phi(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def calculate_historical_expected_shortfall(returns, position_value, confidence: float = 0.95) -> dict:
    r = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if len(r) < 20 or float(position_value or 0) <= 0:
        return {"expected_shortfall": np.nan, "tail_observations": 0, "confidence": confidence, "diagnostic_message": "Dados insuficientes para Expected Shortfall historico."}
    threshold = r.quantile(1 - confidence)
    tail = r[r <= threshold]
    if tail.empty:
        return {"expected_shortfall": np.nan, "tail_observations": 0, "confidence": confidence, "diagnostic_message": "Sem observacoes de cauda."}
    es = abs(float(position_value) * float(tail.mean()))
    return {"expected_shortfall": round(es, 6), "tail_observations": int(len(tail)), "confidence": confidence, "diagnostic_message": "OK"}


def calculate_parametric_expected_shortfall(position_value, volatility, confidence: float = 0.95) -> dict:
    if volatility is None or pd.isna(volatility) or float(position_value or 0) <= 0:
        return {"expected_shortfall": np.nan, "tail_observations": 0, "confidence": confidence, "diagnostic_message": "Dados insuficientes para Expected Shortfall parametrico."}
    z = _z(confidence)
    es = float(position_value) * _daily_vol(float(volatility)) * (_phi(z) / (1 - confidence))
    return {"expected_shortfall": round(abs(es), 6), "tail_observations": 0, "confidence": confidence, "diagnostic_message": "OK"}

