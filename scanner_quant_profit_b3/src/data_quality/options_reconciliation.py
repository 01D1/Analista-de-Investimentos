"""Reconcilia disponibilidade de dados de opcoes."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.data_quality.b3_reconciliation import B3_RECON_COLUMNS
from src.data_quality.source_inventory import table_exists
from src.utils import load_config, project_path


def summarize_options_sources(db_path: str | Path | None = None) -> dict:
    cfg = load_config()
    path = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    summary = {
        "snapshots_count": 0,
        "cotahist_options_count": 0,
        "structures_count": 0,
        "scanner_runs_count": 0,
        "underlyings": [],
        "underlyings_count": 0,
        "maturities_count": 0,
        "strikes_count": 0,
        "snapshot_dates_count": 0,
        "bid_ask_coverage_pct": 0.0,
        "volume_trades_coverage_pct": 0.0,
        "latest_snapshot_date": "",
    }
    if not path.exists():
        summary["error"] = "Banco nao encontrado."
        return summary
    with sqlite3.connect(path) as con:
        if table_exists(con, "options_chain_snapshots"):
            count, underlyings, maturities, strikes, dates, latest = con.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT underlying), COUNT(DISTINCT maturity_date),
                       COUNT(DISTINCT strike), COUNT(DISTINCT trade_date), MAX(COALESCE(trade_date, captured_at))
                FROM options_chain_snapshots
                """
            ).fetchone()
            summary.update(
                {
                    "snapshots_count": int(count or 0),
                    "underlyings_count": int(underlyings or 0),
                    "maturities_count": int(maturities or 0),
                    "strikes_count": int(strikes or 0),
                    "snapshot_dates_count": int(dates or 0),
                    "latest_snapshot_date": str(latest or "")[:10],
                }
            )
            if count:
                bidask = int(con.execute("SELECT COUNT(*) FROM options_chain_snapshots WHERE bid IS NOT NULL AND ask IS NOT NULL").fetchone()[0] or 0)
                vol = int(con.execute("SELECT COUNT(*) FROM options_chain_snapshots WHERE COALESCE(volume,0) > 0 OR COALESCE(trades,0) > 0").fetchone()[0] or 0)
                summary["bid_ask_coverage_pct"] = round(bidask / count * 100, 2)
                summary["volume_trades_coverage_pct"] = round(vol / count * 100, 2)
                summary["underlyings"] = [r[0] for r in con.execute("SELECT DISTINCT underlying FROM options_chain_snapshots WHERE underlying IS NOT NULL LIMIT 200").fetchall()]
        if table_exists(con, "cotahist_daily"):
            try:
                summary["cotahist_options_count"] = int(con.execute("SELECT COUNT(*) FROM cotahist_daily WHERE option_type IS NOT NULL AND option_type <> ''").fetchone()[0] or 0)
            except Exception:
                summary["cotahist_options_count"] = 0
        if table_exists(con, "option_structure_candidates"):
            summary["structures_count"] = int(con.execute("SELECT COUNT(*) FROM option_structure_candidates").fetchone()[0] or 0)
        if table_exists(con, "option_scanner_runs"):
            summary["scanner_runs_count"] = int(con.execute("SELECT COUNT(*) FROM option_scanner_runs").fetchone()[0] or 0)
    return summary


def _row(issue_type: str, severity: str, description: str, command: str, metadata: dict, status: str = "OPEN") -> dict:
    return {
        "source_domain": "OPTIONS",
        "issue_type": issue_type,
        "severity": severity,
        "status": status,
        "description": description,
        "suggested_command": command,
        "executed": False,
        "execution_status": "NOT_EXECUTED",
        "metadata_json": json.dumps(metadata, ensure_ascii=False, default=str),
    }


def compare_options_expectation_vs_available(underlyings: list[str] | None, options_summary: dict) -> pd.DataFrame:
    expected = [u.upper() for u in (underlyings or [])]
    rows = []
    if options_summary.get("snapshots_count", 0) == 0:
        rows.append(_row("NO_CHAIN_SNAPSHOTS", "CRITICAL", "Nao ha snapshots de cadeia de opcoes no banco.", "python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --save-db --csv", options_summary))
    if options_summary.get("bid_ask_coverage_pct", 0) <= 0 and options_summary.get("snapshots_count", 0) > 0:
        rows.append(_row("NO_BID_ASK", "WARNING", "Snapshots de opcoes existem, mas sem cobertura bid/ask.", "python -m src.scanners.options_intelligence_scanner --save-db --csv", options_summary))
    if options_summary.get("snapshot_dates_count", 0) < 2:
        rows.append(_row("NO_HISTORY", "WARNING", "Historico de cadeia de opcoes insuficiente para backtest/walk-forward.", "python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --save-db --csv", options_summary))
    missing_underlyings = sorted(set(expected) - set(str(u).upper() for u in options_summary.get("underlyings", [])))
    if expected and missing_underlyings:
        rows.append(_row("INSUFFICIENT_UNDERLYINGS", "WARNING", f"Underlyings sem cadeia de opcoes: {', '.join(missing_underlyings)}.", "python -m src.scanners.options_intelligence_scanner --underlyings " + " ".join(missing_underlyings) + " --save-db --csv", {"missing_underlyings": missing_underlyings, **options_summary}))
    if options_summary.get("snapshots_count", 0) > 0 and options_summary.get("maturities_count", 0) < 2:
        rows.append(_row("INSUFFICIENT_MATURITIES", "WARNING", "Poucos vencimentos cobertos na cadeia de opcoes.", "python -m src.scanners.options_history_builder --save-db --csv", options_summary))
    if not rows:
        rows.append(_row("OK", "INFO", "Dados de opcoes atendem aos checks basicos.", "", options_summary, status="OK"))
    return pd.DataFrame(rows, columns=B3_RECON_COLUMNS)

