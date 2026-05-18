"""Diagnóstico de cobertura histórica das fontes de sinal em estudo."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


SIGNAL_COVERAGE_COLUMNS = [
    "signal_source",
    "signals_count",
    "tickers_count",
    "first_signal_date",
    "latest_signal_date",
    "active_days_count",
    "regimes_count",
    "useful_cells_count",
    "coverage_pct",
    "coverage_status",
]


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name=?", (table,)).fetchone() is not None


def _read(db_path: str | Path, table: str, date_col: str, ticker_col: str, source: str) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
    try:
        with sqlite3.connect(path) as con:
            if not _table_exists(con, table):
                return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
            cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
            if date_col not in cols or ticker_col not in cols:
                return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
            df = pd.read_sql_query(f"SELECT {date_col} AS trade_date, {ticker_col} AS ticker FROM {table}", con)
    except sqlite3.Error:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
    if df.empty:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.date.astype(str)
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["signal_source"] = source
    return df.dropna(subset=["trade_date", "ticker"])


def _load_regimes(db_path: str | Path, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(path) as con:
            if not _table_exists(con, "market_regime_daily"):
                return pd.DataFrame()
            df = pd.read_sql_query("SELECT * FROM market_regime_daily", con)
    except sqlite3.Error:
        return pd.DataFrame()
    if df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.date.astype(str)
    if start_date:
        df = df[df["trade_date"] >= str(start_date)]
    if end_date:
        df = df[df["trade_date"] <= str(end_date)]
    return df


def _status(count: int, pct: float) -> str:
    if count <= 0:
        return "SEM_DADOS"
    if pct >= 0.70:
        return "COBERTURA_BOA"
    if pct >= 0.50:
        return "COBERTURA_MEDIA"
    if pct > 0:
        return "COBERTURA_FRACA"
    return "COBERTURA_INSUFICIENTE"


def _source_frames(db_path: str | Path, sources: list[str] | None = None) -> dict[str, pd.DataFrame]:
    wanted = {s.lower() for s in sources} if sources else {"quant", "technical", "integrated", "options"}
    frames = {}
    if "quant" in wanted:
        frames["quant"] = _read(db_path, "historical_backtest_results", "trade_date", "ticker", "quant")
    if "technical" in wanted:
        frames["technical"] = _read(db_path, "technical_setup_signals", "trade_date", "ticker", "technical")
    if "integrated" in wanted:
        frames["integrated"] = _read(db_path, "asset_intelligence_snapshots", "trade_date", "ticker", "integrated")
    if "options" in wanted:
        frames["options"] = _read(db_path, "option_structure_candidates", "created_at", "underlying", "options")
    return frames


def summarize_signal_coverage_by_regime(signals_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    """Resume células úteis por fonte e regime quando regimes existirem."""
    columns = ["signal_source", "regime_type", "regime_value", "signals_count", "tickers_count", "active_days_count"]
    if signals_df is None or signals_df.empty or regimes_df is None or regimes_df.empty:
        return pd.DataFrame(columns=columns)
    signals = signals_df.copy()
    regimes = regimes_df.copy()
    signals["trade_date"] = pd.to_datetime(signals["trade_date"], errors="coerce").dt.date.astype(str)
    regimes["trade_date"] = pd.to_datetime(regimes["trade_date"], errors="coerce").dt.date.astype(str)
    merged = signals.merge(regimes, on="trade_date", how="left")
    rows = []
    regime_cols = [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in merged.columns]
    for col in regime_cols:
        work = merged[merged[col].notna()].copy()
        for (source, value), group in work.groupby(["signal_source", col], dropna=False):
            rows.append(
                {
                    "signal_source": source,
                    "regime_type": col,
                    "regime_value": value,
                    "signals_count": int(len(group)),
                    "tickers_count": int(group["ticker"].nunique()),
                    "active_days_count": int(group["trade_date"].nunique()),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def analyze_signal_coverage(db_path: str | Path, start_date: str | None = None, end_date: str | None = None, sources: list[str] | None = None) -> pd.DataFrame:
    """Avalia cobertura de quant, technical, integrated e options, se existirem."""
    regimes = _load_regimes(db_path, start_date, end_date)
    rows = []
    all_signals = []
    for source, df in _source_frames(db_path, sources).items():
        work = df.copy()
        if not work.empty:
            if start_date:
                work = work[work["trade_date"] >= str(start_date)]
            if end_date:
                work = work[work["trade_date"] <= str(end_date)]
            all_signals.append(work)
        signals_count = int(len(work))
        tickers_count = int(work["ticker"].nunique()) if signals_count else 0
        first = str(work["trade_date"].min()) if signals_count else None
        latest = str(work["trade_date"].max()) if signals_count else None
        active_days = int(work["trade_date"].nunique()) if signals_count else 0
        if start_date and end_date:
            expected_days = max(1, len(pd.bdate_range(start_date, end_date)))
        elif signals_count:
            expected_days = max(1, len(pd.bdate_range(first, latest)))
        else:
            expected_days = 0
        if not regimes.empty and signals_count:
            regime_summary = summarize_signal_coverage_by_regime(work, regimes)
            useful_cells = int(len(regime_summary[["regime_type", "regime_value"]].drop_duplicates())) if not regime_summary.empty else 0
            regimes_count = int(regime_summary["regime_value"].nunique()) if not regime_summary.empty else 0
            expected_cells = max(1, regimes[["trade_date"]].drop_duplicates().shape[0] * max(regimes_count, 1))
            coverage_pct = min(1.0, active_days / expected_days) if expected_days else 0.0
        else:
            useful_cells = active_days
            regimes_count = 0
            coverage_pct = active_days / expected_days if expected_days else 0.0
        rows.append(
            {
                "signal_source": source,
                "signals_count": signals_count,
                "tickers_count": tickers_count,
                "first_signal_date": first,
                "latest_signal_date": latest,
                "active_days_count": active_days,
                "regimes_count": regimes_count,
                "useful_cells_count": useful_cells,
                "coverage_pct": round(float(max(0.0, min(1.0, coverage_pct))), 4),
                "coverage_status": _status(signals_count, coverage_pct),
            }
        )
    return pd.DataFrame(rows, columns=SIGNAL_COVERAGE_COLUMNS)


def generate_signal_coverage_report(coverage_df: pd.DataFrame) -> str:
    if coverage_df is None or coverage_df.empty:
        return "Sem população histórica de fontes de sinal em estudo."
    lines = ["Cobertura das fontes de sinal em estudo:"]
    for _, row in coverage_df.iterrows():
        lines.append(
            "- {source}: {count} sinais, {tickers} tickers, {days} dias úteis, {regimes} regimes, {pct:.2%}, {status}".format(
                source=row.get("signal_source"),
                count=int(row.get("signals_count") or 0),
                tickers=int(row.get("tickers_count") or 0),
                days=int(row.get("active_days_count") or 0),
                regimes=int(row.get("regimes_count") or 0),
                pct=float(row.get("coverage_pct") or 0),
                status=row.get("coverage_status"),
            )
        )
    return "\n".join(lines)

