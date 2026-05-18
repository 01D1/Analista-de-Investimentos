"""Rebalanceamento simulado por risco."""
from __future__ import annotations

import pandas as pd

from src.paper.order_model import PaperOrder


def calculate_target_weights_by_risk(risk_snapshots_df: pd.DataFrame, max_weight: float = 0.25) -> pd.DataFrame:
    columns = ["ticker", "target_weight", "risk_score", "reason"]
    if risk_snapshots_df is None or risk_snapshots_df.empty:
        return pd.DataFrame(columns=columns)
    work = risk_snapshots_df.copy()
    work["ticker"] = work["ticker"].astype(str).str.upper()
    vol = pd.to_numeric(work.get("ensemble_vol"), errors="coerce").fillna(pd.to_numeric(work.get("volatility"), errors="coerce")).fillna(1)
    var = pd.to_numeric(work.get("parametric_var_95", work.get("var_95")), errors="coerce").fillna(0)
    blocked = work.get("risk_status", "").astype(str).str.contains("BLOCKED", case=False, na=False)
    work["risk_score"] = (vol.clip(lower=0.0001) * (1 + var.rank(pct=True).fillna(0))).replace(0, 0.0001)
    work["raw_weight"] = 1 / work["risk_score"]
    work.loc[blocked, "raw_weight"] = 0
    total = work["raw_weight"].sum()
    if total <= 0:
        work["target_weight"] = 0.0
    else:
        work["target_weight"] = (work["raw_weight"] / total).clip(upper=float(max_weight))
        clipped_total = work["target_weight"].sum()
        if clipped_total > 0:
            work["target_weight"] = work["target_weight"] / clipped_total
            work["target_weight"] = work["target_weight"].clip(upper=float(max_weight))
    work["reason"] = work.apply(lambda r: "Bloqueado por risco" if str(r.get("risk_status", "")).upper().find("BLOCKED") >= 0 else "Peso inverso ao risco estimado", axis=1)
    return work[["ticker", "target_weight", "risk_score", "reason"]]


def calculate_rebalance_orders(current_positions, target_weights: pd.DataFrame, portfolio_value: float, prices_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if target_weights is None or target_weights.empty or portfolio_value <= 0:
        return pd.DataFrame(columns=["ticker", "side", "quantity", "current_weight", "target_weight", "reason"])
    prices = prices_df.sort_values("trade_date").groupby("ticker").tail(1).set_index("ticker") if prices_df is not None and not prices_df.empty else pd.DataFrame()
    for _, target in target_weights.iterrows():
        ticker = str(target["ticker"]).upper()
        price = float(prices.loc[ticker].get("close")) if ticker in prices.index else None
        if not price or price <= 0:
            continue
        pos = current_positions.get(ticker) if isinstance(current_positions, dict) else None
        current_value = float(pos.market_value) if pos else 0.0
        current_weight = current_value / float(portfolio_value)
        target_weight = float(target["target_weight"])
        delta_value = target_weight * float(portfolio_value) - current_value
        quantity = int(abs(delta_value) / price)
        if quantity <= 0:
            continue
        side = "BUY" if delta_value > 0 else ("CLOSE" if target_weight == 0 else "REDUCE")
        rows.append({"ticker": ticker, "side": side, "quantity": quantity, "current_weight": current_weight, "target_weight": target_weight, "reason": target.get("reason", "Rebalanceamento simulado por risco")})
    return pd.DataFrame(rows)


def rebalance_portfolio_by_risk(portfolio, risk_snapshots_df: pd.DataFrame, prices_df: pd.DataFrame) -> pd.DataFrame:
    weights = calculate_target_weights_by_risk(risk_snapshots_df)
    return calculate_rebalance_orders(portfolio.positions, weights, portfolio.equity, prices_df)

