"""Analise e atribuicao de drawdown da carteira simulada."""
from __future__ import annotations

import pandas as pd

from src.paper.fragility_by_asset import _extract_pnl


def identify_drawdown_periods(equity_curve_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["drawdown_start", "drawdown_trough", "drawdown_recovery", "depth", "duration_days", "recovered", "metadata_json"]
    if equity_curve_df is None or equity_curve_df.empty:
        return pd.DataFrame(columns=columns)
    eq = equity_curve_df.copy()
    eq["trade_date"] = pd.to_datetime(eq["trade_date"], errors="coerce")
    eq["equity"] = pd.to_numeric(eq["equity"], errors="coerce").ffill()
    eq = eq.dropna(subset=["trade_date", "equity"]).sort_values("trade_date")
    if eq.empty:
        return pd.DataFrame(columns=columns)
    peak = eq["equity"].cummax()
    dd = eq["equity"] / peak - 1
    rows = []
    in_dd = False
    start = trough = None
    depth = 0.0
    for i, row in eq.iterrows():
        value = float(dd.loc[i])
        date = row["trade_date"]
        if value < 0 and not in_dd:
            in_dd = True
            start = date
            trough = date
            depth = value
        elif in_dd and value < depth:
            depth = value
            trough = date
        elif in_dd and value >= 0:
            rows.append({"drawdown_start": start.date().isoformat(), "drawdown_trough": trough.date().isoformat(), "drawdown_recovery": date.date().isoformat(), "depth": round(depth, 6), "duration_days": int((date - start).days), "recovered": True, "metadata_json": "{}"})
            in_dd = False
    if in_dd and start is not None and trough is not None:
        last = eq["trade_date"].iloc[-1]
        rows.append({"drawdown_start": start.date().isoformat(), "drawdown_trough": trough.date().isoformat(), "drawdown_recovery": None, "depth": round(depth, 6), "duration_days": int((last - start).days), "recovered": False, "metadata_json": "{}"})
    return pd.DataFrame(rows, columns=columns)


def attribute_drawdown_to_positions(drawdown_periods: pd.DataFrame, positions_df: pd.DataFrame, orders_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["ticker", "contribution", "pnl_during_drawdown", "exposure_during_drawdown", "metadata_json"]
    if drawdown_periods is None or drawdown_periods.empty:
        return pd.DataFrame(columns=columns)
    orders = orders_df.copy() if orders_df is not None else pd.DataFrame()
    positions = positions_df.copy() if positions_df is not None else pd.DataFrame()
    if orders.empty and positions.empty:
        return pd.DataFrame(columns=columns)
    start = str(drawdown_periods.iloc[0]["drawdown_start"])
    end = str(drawdown_periods.iloc[0]["drawdown_recovery"] or drawdown_periods.iloc[0]["drawdown_trough"])
    rows = []
    tickers = set()
    if not orders.empty:
        orders["trade_date"] = orders["trade_date"].astype(str)
        tickers |= set(orders["ticker"].astype(str).str.upper())
    if not positions.empty:
        positions["trade_date"] = positions["trade_date"].astype(str)
        tickers |= set(positions["ticker"].astype(str).str.upper())
    for ticker in sorted(tickers):
        pnl = 0.0
        exposure = 0.0
        if not orders.empty:
            subset = orders[(orders["ticker"].astype(str).str.upper() == ticker) & (orders["trade_date"] >= start) & (orders["trade_date"] <= end)]
            pnl = float(subset.apply(_extract_pnl, axis=1).sum()) if not subset.empty else 0.0
        if not positions.empty:
            pos = positions[(positions["ticker"].astype(str).str.upper() == ticker) & (positions["trade_date"] >= start) & (positions["trade_date"] <= end)]
            exposure = float(pd.to_numeric(pos.get("market_value"), errors="coerce").fillna(0).mean()) if not pos.empty else 0.0
        rows.append({"ticker": ticker, "contribution": pnl, "pnl_during_drawdown": pnl, "exposure_during_drawdown": exposure, "metadata_json": "{}"})
    return pd.DataFrame(rows, columns=columns)


def generate_drawdown_report(drawdown_df: pd.DataFrame, attribution_df: pd.DataFrame) -> str:
    if drawdown_df is None or drawdown_df.empty:
        return "Nenhum periodo de drawdown identificado na carteira simulada."
    worst = drawdown_df.sort_values("depth").iloc[0]
    return f"Concentracao de drawdown: pior profundidade {float(worst['depth']):.4f} entre {worst['drawdown_start']} e {worst['drawdown_trough']}."
