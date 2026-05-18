"""Score de fragilidade para carteira simulada."""
from __future__ import annotations

import pandas as pd


def calculate_fragility_score(row) -> dict:
    data = dict(row)
    trades = float(data.get("trades_count", data.get("trades", 0)) or 0)
    net_pnl = float(data.get("net_pnl", 0) or 0)
    cost_drag = abs(float(data.get("cost_drag", data.get("total_cost_drag", 0)) or 0))
    drawdown = abs(float(data.get("drawdown_contribution", data.get("max_drawdown", 0)) or 0))
    concentration = abs(float(data.get("concentration_pct", data.get("contribution_pct", 0)) or 0))
    win_rate = float(data.get("win_rate", 0) or 0)
    turnover = float(data.get("turnover", trades) or 0)
    if trades < 3:
        return {"fragility_score": 100.0, "fragility_class": "DADOS_INSUFICIENTES"}
    score = 0.0
    if net_pnl < 0:
        score += min(30.0, abs(net_pnl) / max(abs(net_pnl) + 1, 1) * 30)
    score += min(20.0, cost_drag / max(abs(net_pnl) + cost_drag + 1, 1) * 40)
    score += min(20.0, drawdown * 100)
    score += min(15.0, concentration * 30)
    if win_rate < 0.45:
        score += min(10.0, (0.45 - win_rate) * 40)
    if turnover > 100:
        score += min(5.0, (turnover - 100) / 50)
    score = round(float(max(0, min(score, 100))), 2)
    if score < 25:
        klass = "ROBUSTO"
    elif score < 50:
        klass = "OBSERVACAO"
    elif score < 75:
        klass = "FRAGIL"
    else:
        klass = "CRITICO"
    return {"fragility_score": score, "fragility_class": klass}


def add_fragility_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    out = df.copy()
    scores = out.apply(calculate_fragility_score, axis=1, result_type="expand")
    out["fragility_score"] = scores["fragility_score"]
    out["fragility_class"] = scores["fragility_class"]
    return out
