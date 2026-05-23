"""Diagnóstico de custo de liquidez no paper trading."""
from __future__ import annotations

import pandas as pd

from src.paper.cost_structure_diagnostics import _num


def _classify(cost_pct: float, participation: float | None, has_data: bool) -> str:
    if not has_data:
        return "DATA_INSUFFICIENT"
    part = float(participation or 0)
    if cost_pct < 0.001 and part < 0.02:
        return "LIQUIDITY_OK"
    if cost_pct < 0.003 and part < 0.05:
        return "LIQUIDITY_WARNING"
    if cost_pct < 0.01 and part < 0.10:
        return "LIQUIDITY_COSTLY"
    return "LIQUIDITY_UNTRADEABLE"


def analyze_liquidity_costs(orders_df: pd.DataFrame, market_data_df: pd.DataFrame | None = None) -> dict:
    columns = ["ticker", "trades_count", "avg_volume", "avg_financial_volume", "total_notional", "avg_cost_pct", "avg_slippage_pct", "participation_rate", "above_participation_threshold", "liquidity_class", "metadata_json"]
    if orders_df is None or orders_df.empty:
        return {"summary": {"liquidity_class": "DATA_INSUFFICIENT", "problematic_assets_count": 0, "metadata_json": "{}"}, "liquidity_by_ticker": pd.DataFrame(columns=columns)}
    work = orders_df.copy()
    work["trade_date"] = work.get("trade_date", "").astype(str)
    work["ticker"] = work.get("ticker", "UNKNOWN").fillna("UNKNOWN").astype(str).str.upper()
    work["quantity"] = _num(work["quantity"] if "quantity" in work.columns else pd.Series(0, index=work.index)).abs()
    price = work["simulated_execution_price"] if "simulated_execution_price" in work.columns else work["theoretical_price"] if "theoretical_price" in work.columns else pd.Series(0, index=work.index)
    work["price"] = _num(price)
    work["notional"] = work["quantity"] * work["price"]
    work["execution_cost"] = _num(work["execution_cost"] if "execution_cost" in work.columns else 0)
    work["slippage_cost"] = _num(work["slippage_cost"] if "slippage_cost" in work.columns else 0)
    has_market = market_data_df is not None and not market_data_df.empty and {"ticker"}.issubset(market_data_df.columns)
    if has_market:
        market = market_data_df.copy()
        market["ticker"] = market["ticker"].astype(str).str.upper()
        if "trade_date" in market.columns:
            market["trade_date"] = market["trade_date"].astype(str)
            work = work.merge(market, on=["trade_date", "ticker"], how="left", suffixes=("", "_market"))
        else:
            work = work.merge(market, on="ticker", how="left", suffixes=("", "_market"))
    volume = _num(work["volume"] if "volume" in work.columns else pd.Series(0, index=work.index))
    close = _num(work["close"] if "close" in work.columns else work["price"])
    financial_volume = _num(work["financial_volume"] if "financial_volume" in work.columns else volume * close)
    work["volume"] = volume
    work["financial_volume"] = financial_volume
    work["cost_pct"] = pd.to_numeric(work["execution_cost"] / work["notional"].replace(0, pd.NA), errors="coerce").fillna(0)
    work["slippage_pct"] = pd.to_numeric(work["slippage_cost"] / work["notional"].replace(0, pd.NA), errors="coerce").fillna(0)
    rows = []
    for ticker, group in work.groupby("ticker"):
        notional = float(group["notional"].sum())
        avg_fin = float(group["financial_volume"].replace(0, pd.NA).dropna().mean() or 0)
        participation = notional / max(avg_fin, 1.0)
        cost_pct = float(group["cost_pct"].mean() + group["slippage_pct"].mean())
        liq_class = _classify(cost_pct, participation, has_market and avg_fin > 0)
        rows.append(
            {
                "ticker": ticker,
                "trades_count": int(len(group)),
                "avg_volume": round(float(group["volume"].replace(0, pd.NA).dropna().mean() or 0), 6),
                "avg_financial_volume": round(avg_fin, 6),
                "total_notional": round(notional, 6),
                "avg_cost_pct": round(float(group["cost_pct"].mean()), 6),
                "avg_slippage_pct": round(float(group["slippage_pct"].mean()), 6),
                "participation_rate": round(float(participation), 6),
                "above_participation_threshold": bool(participation > 0.05),
                "liquidity_class": liq_class,
                "metadata_json": "{}",
            }
        )
    by_ticker = pd.DataFrame(rows, columns=columns).sort_values(["liquidity_class", "participation_rate"], ascending=[False, False]).reset_index(drop=True)
    problematic = by_ticker["liquidity_class"].isin(["LIQUIDITY_COSTLY", "LIQUIDITY_UNTRADEABLE"]).sum() if not by_ticker.empty else 0
    summary_class = "DATA_INSUFFICIENT" if not has_market else "LIQUIDITY_COSTLY" if problematic else "LIQUIDITY_OK"
    return {"summary": {"liquidity_class": summary_class, "problematic_assets_count": int(problematic), "metadata_json": "{}"}, "liquidity_by_ticker": by_ticker}
