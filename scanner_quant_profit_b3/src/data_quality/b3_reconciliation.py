"""Reconcilia arquivos B3 COTAHIST raw com tabelas SQLite."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

from src.data_quality.file_manifest import calculate_file_checksum
from src.data_quality.source_inventory import resolve_path
from src.utils import load_config, project_path


B3_RECON_COLUMNS = [
    "source_domain",
    "issue_type",
    "severity",
    "status",
    "description",
    "suggested_command",
    "executed",
    "execution_status",
    "metadata_json",
]


def _year(path: Path) -> str:
    m = re.search(r"A(\d{4})", path.name.upper())
    return m.group(1) if m else ""


def summarize_b3_raw_files(raw_dir: str | Path = "data/raw") -> pd.DataFrame:
    raw = resolve_path(raw_dir) or Path(raw_dir)
    files = []
    if raw.exists():
        files = sorted(raw.glob("COTAHIST_A*.ZIP")) + sorted(raw.glob("COTAHIST_A*.zip")) + sorted(raw.glob("COTAHIST_A*.TXT")) + sorted(raw.glob("COTAHIST_A*.txt"))
    rows = []
    for path in files:
        stat = path.stat()
        rows.append(
            {
                "file_path": str(path.resolve()),
                "file_name": path.name,
                "year": _year(path),
                "size_bytes": int(stat.st_size),
                "modified_at": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
                "checksum": calculate_file_checksum(path),
                "status_raw": "OK" if stat.st_size > 0 else "EMPTY",
            }
        )
    return pd.DataFrame(rows, columns=["file_path", "file_name", "year", "size_bytes", "modified_at", "checksum", "status_raw"])


def _sqlite_objects(con) -> list[str]:
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')").fetchall()]


def _cols(con, table: str) -> list[str]:
    try:
        return [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def summarize_b3_sqlite(db_path: str | Path | None = None) -> pd.DataFrame:
    cfg = load_config()
    path = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    rows = []
    if not path.exists():
        return pd.DataFrame(columns=["table_name", "rows_count", "min_trade_date", "max_trade_date", "years_available", "tickers_count", "options_count", "latest_date"])
    candidates = ["cotahist_daily", "b3_quotes", "market_daily"]
    try:
        with sqlite3.connect(path) as con:
            objects = set(_sqlite_objects(con))
            for table in [t for t in candidates if t in objects]:
                cols = _cols(con, table)
                date_col = next((c for c in ["trade_date", "date", "data"] if c in cols), None)
                ticker_col = next((c for c in ["ticker", "asset", "symbol"] if c in cols), None)
                option_col = next((c for c in ["option_type", "asset_type"] if c in cols), None)
                count = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] or 0)
                min_date = max_date = ""
                years = []
                if date_col and count:
                    min_date, max_date = con.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {table}").fetchone()
                    years = [str(r[0]) for r in con.execute(f"SELECT DISTINCT substr({date_col}, 1, 4) FROM {table} WHERE {date_col} IS NOT NULL ORDER BY 1").fetchall()]
                tickers = int(con.execute(f"SELECT COUNT(DISTINCT {ticker_col}) FROM {table}").fetchone()[0] or 0) if ticker_col else 0
                options = 0
                if option_col:
                    if option_col == "asset_type":
                        options = int(con.execute(f"SELECT COUNT(*) FROM {table} WHERE lower({option_col}) LIKE '%option%'").fetchone()[0] or 0)
                    else:
                        options = int(con.execute(f"SELECT COUNT(*) FROM {table} WHERE {option_col} IS NOT NULL AND {option_col} <> ''").fetchone()[0] or 0)
                rows.append(
                    {
                        "table_name": table,
                        "rows_count": count,
                        "min_trade_date": min_date or "",
                        "max_trade_date": max_date or "",
                        "years_available": ",".join(years),
                        "tickers_count": tickers,
                        "options_count": options,
                        "latest_date": max_date or "",
                    }
                )
    except Exception as exc:
        rows.append({"table_name": "ERROR", "rows_count": 0, "min_trade_date": "", "max_trade_date": "", "years_available": "", "tickers_count": 0, "options_count": 0, "latest_date": "", "error": str(exc)})
    return pd.DataFrame(rows)


def _issue(issue_type: str, severity: str, description: str, command: str = "", metadata: dict | None = None, status: str = "OPEN") -> dict:
    return {
        "source_domain": "B3_COTAHIST",
        "issue_type": issue_type,
        "severity": severity,
        "status": status,
        "description": description,
        "suggested_command": command,
        "executed": False,
        "execution_status": "NOT_EXECUTED",
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }


def compare_b3_raw_vs_sqlite(raw_summary: pd.DataFrame, sqlite_summary: pd.DataFrame) -> pd.DataFrame:
    raw_years = sorted(set(raw_summary.get("year", pd.Series(dtype=str)).dropna().astype(str)) - {""}) if raw_summary is not None and not raw_summary.empty else []
    db_years: set[str] = set()
    rows = []
    if sqlite_summary is not None and not sqlite_summary.empty:
        for years in sqlite_summary.get("years_available", pd.Series(dtype=str)).fillna(""):
            db_years.update(y for y in str(years).split(",") if y)
    db_rows = int(sqlite_summary["rows_count"].fillna(0).sum()) if sqlite_summary is not None and not sqlite_summary.empty and "rows_count" in sqlite_summary.columns else 0
    options_count = int(sqlite_summary["options_count"].fillna(0).sum()) if sqlite_summary is not None and not sqlite_summary.empty and "options_count" in sqlite_summary.columns else 0
    if raw_years and db_rows == 0:
        rows.append(_issue("RAW_PRESENT_DB_EMPTY", "CRITICAL", f"Arquivos COTAHIST raw existem para {', '.join(raw_years)}, mas o SQLite nao possui registros B3 processados.", "python -m src.collectors.b3_cotahist_collector --all", {"raw_years": raw_years}))
    for year in raw_years:
        if year not in db_years:
            rows.append(_issue("DB_MISSING_YEAR", "WARNING", f"Arquivo raw COTAHIST {year} existe, mas o SQLite nao tem registros desse ano.", f"python -m src.collectors.b3_cotahist_collector --year {year}", {"year": year}))
    if raw_years and db_years and max(raw_years) > max(db_years):
        year = max(raw_years)
        rows.append(_issue("RAW_NEWER_THAN_DB", "WARNING", f"O raw mais recente ({year}) e posterior ao ultimo ano no banco ({max(db_years)}).", f"python -m src.collectors.b3_cotahist_collector --year {year}", {"raw_years": raw_years, "db_years": sorted(db_years)}))
    if db_rows > 0 and options_count == 0:
        rows.append(_issue("OPTIONS_MISSING", "WARNING", "SQLite B3 possui dados, mas nenhuma opcao foi identificada.", "python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --save-db --csv", {"options_count": options_count}))
    if not raw_years and db_rows == 0:
        rows.append(_issue("INSUFFICIENT_DATA", "CRITICAL", "Nao ha arquivos raw COTAHIST nem registros SQLite suficientes para reconciliar.", "python -m src.collectors.b3_cotahist_collector --year 2026", {}))
    if not rows:
        rows.append(_issue("OK", "INFO", "B3 raw e SQLite parecem reconciliados para os anos disponiveis.", "", {"raw_years": raw_years, "db_years": sorted(db_years)}, status="OK"))
    result = pd.DataFrame(rows, columns=B3_RECON_COLUMNS)
    result["status_reconciliation"] = result["issue_type"].where(result["issue_type"] != "OK", "OK")
    return result


def generate_b3_reconciliation_report(result_df: pd.DataFrame) -> str:
    if result_df is None or result_df.empty:
        return "Sem resultados de reconciliacao B3."
    lines = []
    for _, row in result_df.iterrows():
        line = str(row.get("description", ""))
        cmd = str(row.get("suggested_command", ""))
        if cmd:
            line += f" Execute: {cmd}"
        lines.append(line)
    return "\n".join(lines)

