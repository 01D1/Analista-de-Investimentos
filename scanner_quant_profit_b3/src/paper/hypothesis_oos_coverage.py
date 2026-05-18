"""Diagnostico de cobertura para validacao OOS de hipoteses."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.paper.hypothesis_oos_validation import create_hypothesis_oos_windows
from src.scanners.paper_trading_simulation import load_paper_signals


COVERAGE_COLUMNS = [
    "window_id",
    "scenario_name",
    "signal_source",
    "regime_filter",
    "start_date",
    "end_date",
    "signals_count",
    "price_days_count",
    "tickers_count",
    "useful_cell",
    "source_coverage_status",
    "message",
    "metadata_json",
]


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _read_table(db_path: str | Path, table: str) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con, table):
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM {table}", con)
    except sqlite3.Error:
        return pd.DataFrame()


def _normalize(df: pd.DataFrame, source: str, start: str | None, end: str | None, signal_type: str = "OBSERVAR") -> pd.DataFrame:
    if df is None or df.empty or "ticker" not in df.columns:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source", "signal_type"])
    out = df.copy()
    if "trade_date" not in out.columns:
        out["trade_date"] = start or pd.Timestamp.today().date().isoformat()
    out["trade_date"] = out["trade_date"].astype(str)
    out["ticker"] = out["ticker"].astype(str).str.upper()
    out["signal_source"] = source
    if "signal_type" not in out.columns:
        out["signal_type"] = signal_type
    if start:
        out = out[out["trade_date"] >= str(start)]
    if end:
        out = out[out["trade_date"] <= str(end)]
    return out


def load_expanded_paper_signals(db_path: str | Path, signal_sources: list[str] | None = None, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Carrega sinais do paper e expande cobertura usando somente tabelas ja persistidas."""
    wanted = {s.lower() for s in (signal_sources or ["quant", "technical", "integrated", "all"])}
    include_all = "all" in wanted
    frames = [load_paper_signals(db_path, "all", start, end)]
    if include_all or "technical" in wanted:
        bt = _normalize(_read_table(db_path, "technical_backtest_results"), "technical", start, end)
        setups = _normalize(_read_table(db_path, "technical_setup_signals"), "technical", start, end)
        features = _normalize(_read_table(db_path, "technical_feature_snapshots"), "technical", start, end)
        frames.extend([bt, setups, features])
    if include_all or "integrated" in wanted:
        integrated = _normalize(_read_table(db_path, "asset_intelligence_snapshots"), "integrated", start, end)
        frames.append(integrated)
    if include_all or "quant" in wanted:
        quant = _normalize(_read_table(db_path, "historical_backtest_results"), "quant", start, end)
        frames.append(quant)
    out = pd.concat([f for f in frames if f is not None and not f.empty], ignore_index=True) if frames else pd.DataFrame()
    if out.empty:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source", "signal_type"])
    return out.sort_values(["trade_date", "ticker", "signal_source"]).drop_duplicates(["trade_date", "ticker", "signal_source"])


def _filter_regime_dates(regimes_df: pd.DataFrame | None, regime_filter: str) -> set[str] | None:
    if regimes_df is None or regimes_df.empty or not regime_filter or "trade_date" not in regimes_df.columns:
        return None
    cols = [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in regimes_df.columns]
    if not cols:
        return None
    mask = pd.Series(False, index=regimes_df.index)
    for col in cols:
        mask = mask | regimes_df[col].astype(str).str.upper().eq(str(regime_filter).upper())
    return set(regimes_df.loc[mask, "trade_date"].astype(str))


def diagnose_oos_coverage(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    regimes_df: pd.DataFrame | None,
    scenarios: pd.DataFrame,
    start_date: str,
    end_date: str,
    train_months: int = 2,
    test_months: int = 1,
    min_signals_per_window: int = 1,
    min_price_days_per_window: int = 5,
) -> pd.DataFrame:
    if not start_date or not end_date:
        return pd.DataFrame(columns=COVERAGE_COLUMNS)
    windows = create_hypothesis_oos_windows(start_date, end_date, train_months=train_months, test_months=test_months)
    if windows.empty or scenarios is None or scenarios.empty:
        return pd.DataFrame(columns=COVERAGE_COLUMNS)
    signals = signals_df.copy() if signals_df is not None else pd.DataFrame()
    prices = prices_df.copy() if prices_df is not None else pd.DataFrame()
    for df in [signals, prices]:
        if not df.empty and "trade_date" in df.columns:
            df["trade_date"] = df["trade_date"].astype(str)
    rows = []
    for _, window in windows.iterrows():
        start = str(window["test_start"])
        end = str(window["test_end"])
        for _, scenario in scenarios.iterrows():
            source = str(scenario.get("signal_source", "quant")).lower()
            regime = str(scenario.get("regime_filter", "") or "")
            allowed_dates = _filter_regime_dates(regimes_df, regime)
            sig = signals[(signals.get("trade_date", pd.Series(dtype=str)).astype(str) >= start) & (signals.get("trade_date", pd.Series(dtype=str)).astype(str) <= end)].copy() if not signals.empty else pd.DataFrame()
            if not sig.empty and "signal_source" in sig.columns:
                sig = sig[sig["signal_source"].astype(str).str.lower().eq(source)]
            px = prices[(prices.get("trade_date", pd.Series(dtype=str)).astype(str) >= start) & (prices.get("trade_date", pd.Series(dtype=str)).astype(str) <= end)].copy() if not prices.empty else pd.DataFrame()
            if allowed_dates is not None:
                sig = sig[sig["trade_date"].astype(str).isin(allowed_dates)] if not sig.empty else sig
                px = px[px["trade_date"].astype(str).isin(allowed_dates)] if not px.empty else px
            signals_count = int(len(sig))
            price_days = int(px["trade_date"].nunique()) if not px.empty and "trade_date" in px.columns else 0
            tickers_count = int(sig["ticker"].nunique()) if not sig.empty and "ticker" in sig.columns else 0
            useful = signals_count >= min_signals_per_window and price_days >= min_price_days_per_window
            if useful:
                status = "COVERAGE_USEFUL"
                message = "Janela/cenario com amostra minima para simulacao OOS."
            elif signals_count == 0:
                status = "COVERAGE_NO_SIGNALS"
                message = "Sem sinais para fonte/regime nesta janela."
            elif price_days < min_price_days_per_window:
                status = "COVERAGE_LOW_PRICE_DAYS"
                message = "Historico de precos insuficiente nesta janela."
            else:
                status = "COVERAGE_LOW_SAMPLE"
                message = "Amostra abaixo do minimo configurado."
            rows.append(
                {
                    "window_id": int(window["window_id"]),
                    "scenario_name": scenario.get("scenario_name"),
                    "signal_source": source,
                    "regime_filter": regime,
                    "start_date": start,
                    "end_date": end,
                    "signals_count": signals_count,
                    "price_days_count": price_days,
                    "tickers_count": tickers_count,
                    "useful_cell": bool(useful),
                    "source_coverage_status": status,
                    "message": message,
                    "metadata_json": json.dumps({"scenario": scenario.to_dict(), "window": window.to_dict()}, ensure_ascii=False, default=str),
                }
            )
    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)


def filter_scenarios_by_coverage(scenarios: pd.DataFrame, coverage_df: pd.DataFrame) -> pd.DataFrame:
    if scenarios is None or scenarios.empty or coverage_df is None or coverage_df.empty:
        return scenarios.copy() if scenarios is not None else pd.DataFrame()
    useful = coverage_df[coverage_df["useful_cell"].astype(bool)]
    if useful.empty:
        return scenarios.head(1).copy()
    keys = set(zip(useful["scenario_name"].astype(str), useful["signal_source"].astype(str)))
    mask = scenarios.apply(lambda row: (str(row.get("scenario_name")), str(row.get("signal_source"))) in keys, axis=1)
    filtered = scenarios[mask].copy()
    return filtered if not filtered.empty else scenarios.head(1).copy()


def summarize_coverage(coverage_df: pd.DataFrame) -> dict:
    if coverage_df is None or coverage_df.empty:
        return {
            "coverage_cells": 0,
            "useful_cells": 0,
            "useful_cells_pct": 0.0,
            "sources_with_useful_data": 0,
            "regimes_with_useful_data": 0,
            "coverage_status": "COVERAGE_INSUFFICIENT",
        }
    useful = coverage_df["useful_cell"].astype(bool)
    useful_sources = coverage_df.loc[useful, "signal_source"].nunique()
    useful_regimes = coverage_df.loc[useful & coverage_df["regime_filter"].astype(str).ne(""), "regime_filter"].nunique()
    pct = float(useful.mean())
    if pct >= 0.70:
        status = "COVERAGE_GOOD"
    elif pct >= 0.40:
        status = "COVERAGE_PARTIAL"
    else:
        status = "COVERAGE_INSUFFICIENT"
    return {
        "coverage_cells": int(len(coverage_df)),
        "useful_cells": int(useful.sum()),
        "useful_cells_pct": round(pct, 4),
        "sources_with_useful_data": int(useful_sources),
        "regimes_with_useful_data": int(useful_regimes),
        "coverage_status": status,
    }


def summarize_source_coverage_requirements(
    coverage_df: pd.DataFrame,
    min_useful_coverage_pct: float = 0.5,
    min_signals_per_source: int = 30,
) -> dict:
    """Avalia cobertura mínima por fonte dentro das células OOS diagnosticadas."""
    if coverage_df is None or coverage_df.empty:
        return {
            "requirements_status": "COVERAGE_INSUFFICIENT",
            "excluded_sources": [],
            "passed_sources": [],
            "source_summary": [],
            "message": "Sem células de cobertura OOS para validação de amostra.",
        }
    rows = []
    passed = []
    excluded = []
    for source, group in coverage_df.groupby(coverage_df["signal_source"].astype(str).str.lower(), dropna=False):
        useful = group["useful_cell"].astype(bool)
        useful_pct = float(useful.mean()) if len(group) else 0.0
        signals_count = int(pd.to_numeric(group.get("signals_count"), errors="coerce").fillna(0).sum())
        tickers_count = int(group.get("tickers_count", pd.Series(dtype=int)).max() or 0)
        status = "COVERAGE_REQUIREMENTS_PASS"
        reasons = []
        if useful_pct < float(min_useful_coverage_pct):
            reasons.append("cobertura útil abaixo do mínimo")
        if signals_count < int(min_signals_per_source):
            reasons.append("sinais abaixo do mínimo")
        if reasons:
            status = "COVERAGE_INSUFFICIENT"
            excluded.append(str(source))
        else:
            passed.append(str(source))
        rows.append(
            {
                "signal_source": str(source),
                "signals_count": signals_count,
                "tickers_count": tickers_count,
                "coverage_cells": int(len(group)),
                "useful_cells": int(useful.sum()),
                "useful_cells_pct": round(useful_pct, 4),
                "requirements_status": status,
                "message": "OK" if not reasons else "Cobertura insuficiente: " + "; ".join(reasons),
            }
        )
    overall = "COVERAGE_REQUIREMENTS_PASS" if rows and not excluded else "COVERAGE_INSUFFICIENT"
    return {
        "requirements_status": overall,
        "excluded_sources": excluded,
        "passed_sources": passed,
        "source_summary": rows,
        "message": "Cobertura por fonte suficiente." if overall == "COVERAGE_REQUIREMENTS_PASS" else "Uma ou mais fontes foram excluídas por cobertura insuficiente.",
    }


def compare_coverage_before_after(before_df: pd.DataFrame, after_df: pd.DataFrame) -> dict:
    before = summarize_coverage(before_df)
    after = summarize_coverage(after_df)
    return {
        "before_useful_cells": before["useful_cells"],
        "after_useful_cells": after["useful_cells"],
        "useful_cells_delta": after["useful_cells"] - before["useful_cells"],
        "before_useful_cells_pct": before["useful_cells_pct"],
        "after_useful_cells_pct": after["useful_cells_pct"],
        "useful_cells_pct_delta": round(after["useful_cells_pct"] - before["useful_cells_pct"], 4),
        "before_status": before["coverage_status"],
        "after_status": after["coverage_status"],
        "sources_delta": after["sources_with_useful_data"] - before["sources_with_useful_data"],
        "regimes_delta": after["regimes_with_useful_data"] - before["regimes_with_useful_data"],
    }
