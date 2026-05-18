"""Decomposição de P&L da carteira simulada."""
from __future__ import annotations

import pandas as pd


def _pnl_series(df: pd.DataFrame) -> pd.Series:
    if "metadata_trade_pnl" in df.columns:
        return pd.to_numeric(df["metadata_trade_pnl"], errors="coerce").fillna(0)
    return pd.Series([0.0] * len(df), index=df.index)


def _aggregate(df: pd.DataFrame, group_col: str, attribution_type: str) -> pd.DataFrame:
    columns = ["attribution_type", "bucket", "trades", "gross_pnl", "net_pnl", "win_rate", "avg_return", "contribution_pct", "metadata_json"]
    if df is None or df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=columns)
    work = df.copy()
    work["pnl"] = _pnl_series(work)
    total = work["pnl"].sum()
    rows = []
    for bucket, group in work.groupby(group_col, dropna=False):
        pnl = group["pnl"]
        rows.append(
            {
                "attribution_type": attribution_type,
                "bucket": str(bucket),
                "trades": int(len(group)),
                "gross_pnl": float(pnl[pnl > 0].sum()),
                "net_pnl": float(pnl.sum()),
                "win_rate": float((pnl > 0).mean()) if len(pnl) else 0.0,
                "avg_return": float(pnl.mean()) if len(pnl) else 0.0,
                "contribution_pct": float(pnl.sum() / total) if total else 0.0,
                "metadata_json": "{}",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def attribute_pnl_by_signal_source(orders_df: pd.DataFrame, positions_df: pd.DataFrame | None = None) -> pd.DataFrame:
    frames = []
    for col in ["signal_source", "setup_type", "quant_signal_type", "technical_setup", "integrated_status"]:
        if orders_df is not None and col in orders_df.columns:
            frames.append(_aggregate(orders_df, col, col))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["attribution_type", "bucket", "trades", "gross_pnl", "net_pnl", "win_rate", "avg_return", "contribution_pct", "metadata_json"])


def attribute_pnl_by_risk_bucket(positions_df: pd.DataFrame, risk_df: pd.DataFrame) -> pd.DataFrame:
    if positions_df is None or positions_df.empty or risk_df is None or risk_df.empty:
        return pd.DataFrame()
    merged = positions_df.merge(risk_df, on="ticker", how="left", suffixes=("", "_risk"))
    merged["metadata_trade_pnl"] = pd.to_numeric(merged.get("realized_pnl"), errors="coerce").fillna(0) + pd.to_numeric(merged.get("unrealized_pnl"), errors="coerce").fillna(0)
    frames = [_aggregate(merged, col, col) for col in ["volatility_regime", "risk_status", "limiting_factor"] if col in merged.columns]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def attribute_pnl_by_regime(positions_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    if positions_df is None or positions_df.empty or regimes_df is None or regimes_df.empty:
        return pd.DataFrame()
    merged = positions_df.merge(regimes_df, on="trade_date", how="left")
    merged["metadata_trade_pnl"] = pd.to_numeric(merged.get("realized_pnl"), errors="coerce").fillna(0) + pd.to_numeric(merged.get("unrealized_pnl"), errors="coerce").fillna(0)
    return _aggregate(merged, "primary_regime", "primary_regime") if "primary_regime" in merged.columns else pd.DataFrame()


def attribute_pnl_by_event_context(positions_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    if positions_df is None or positions_df.empty or events_df is None or events_df.empty:
        return pd.DataFrame()
    merged = positions_df.merge(events_df, on=["trade_date", "ticker"], how="left")
    merged["metadata_trade_pnl"] = pd.to_numeric(merged.get("realized_pnl"), errors="coerce").fillna(0) + pd.to_numeric(merged.get("unrealized_pnl"), errors="coerce").fillna(0)
    return _aggregate(merged, "event_context_type", "event_context_type") if "event_context_type" in merged.columns else pd.DataFrame()


def generate_pnl_attribution_report(attribution_df: pd.DataFrame) -> str:
    if attribution_df is None or attribution_df.empty:
        return "Sem dados suficientes para decomposição de P&L simulado."
    top = attribution_df.sort_values("net_pnl", ascending=False).iloc[0]
    return f"Principal contribuição de P&L simulado: {top['attribution_type']}={top['bucket']} com net_pnl {top['net_pnl']:.2f}."

