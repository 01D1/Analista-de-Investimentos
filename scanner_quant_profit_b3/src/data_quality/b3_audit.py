"""Auditoria dos arquivos B3 COTAHIST e sua carga no SQLite."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from src.data_quality.source_inventory import make_audit_row, resolve_path, table_exists


def _year_from_name(path: Path) -> str | None:
    match = re.search(r"A(\d{4})", path.name.upper())
    return match.group(1) if match else None


def _db_summary(db_path: str | Path | None) -> dict:
    summary = {"records_count": 0, "latest_date": "", "tickers_count": 0, "market_types": {}, "options_count": 0}
    if not db_path or not Path(db_path).exists():
        return summary
    try:
        with sqlite3.connect(db_path) as con:
            if not table_exists(con, "cotahist_daily"):
                return summary
            row = con.execute("SELECT COUNT(*), MAX(trade_date), COUNT(DISTINCT ticker) FROM cotahist_daily").fetchone()
            summary.update({"records_count": int(row[0] or 0), "latest_date": row[1] or "", "tickers_count": int(row[2] or 0)})
            try:
                summary["market_types"] = dict(con.execute("SELECT market_type, COUNT(*) FROM cotahist_daily GROUP BY market_type").fetchall())
            except Exception:
                pass
            try:
                summary["options_count"] = int(con.execute("SELECT COUNT(*) FROM cotahist_daily WHERE option_type IS NOT NULL AND option_type <> ''").fetchone()[0] or 0)
            except Exception:
                summary["options_count"] = 0
    except Exception:
        pass
    return summary


def compare_b3_raw_vs_db(raw_summary: dict, db_summary: dict) -> dict:
    issues: list[str] = []
    if raw_summary.get("files_count", 0) > 0 and db_summary.get("records_count", 0) == 0:
        issues.append("Arquivos raw existem, mas nao ha registros processados no banco.")
    if db_summary.get("latest_date") and raw_summary.get("latest_year"):
        if str(db_summary["latest_date"])[:4] < str(raw_summary["latest_year"]):
            issues.append("Banco parece desatualizado em relacao ao ano raw mais recente.")
    if db_summary.get("options_count", 0) == 0:
        issues.append("Nao ha opcoes identificadas no banco COTAHIST.")
    status = "OK" if not issues else "WARNING"
    return {"status": status, "issues": issues, "message": "; ".join(issues) if issues else "Raw e banco sem divergencia relevante detectada."}


def audit_b3_cotahist(raw_dir: str | Path = "data/raw", processed_dir: str | Path = "data/processed", db_path: str | Path | None = None) -> dict:
    raw_path = resolve_path(raw_dir) or Path(raw_dir)
    processed_path = resolve_path(processed_dir) or Path(processed_dir)
    zips = sorted(raw_path.glob("COTAHIST_A*.ZIP")) + sorted(raw_path.glob("COTAHIST_A*.zip")) if raw_path.exists() else []
    txts = sorted(raw_path.glob("COTAHIST_A*.TXT")) + sorted(raw_path.glob("COTAHIST_A*.txt")) if raw_path.exists() else []
    if processed_path.exists():
        txts += sorted(processed_path.glob("COTAHIST_A*.TXT")) + sorted(processed_path.glob("COTAHIST_A*.txt"))
    years = sorted({y for p in [*zips, *txts] if (y := _year_from_name(p))})
    raw_summary = {
        "raw_dir": str(raw_path),
        "processed_dir": str(processed_path),
        "zip_files": [str(p) for p in zips],
        "txt_files": [str(p) for p in txts],
        "files_count": len(zips) + len(txts),
        "years": years,
        "latest_year": years[-1] if years else "",
    }
    db_summary = _db_summary(db_path)
    comparison = compare_b3_raw_vs_db(raw_summary, db_summary)
    available = raw_summary["files_count"] > 0 or db_summary["records_count"] > 0
    if not available:
        status = "MISSING"
        message = "Nenhum arquivo COTAHIST raw/processado e nenhum registro no banco foram encontrados."
    else:
        status = comparison["status"]
        message = comparison["message"]
        if db_summary["records_count"] == 0:
            status = "WARNING"
    return make_audit_row(
        source_name="b3_cotahist",
        source_type="MARKET_DATA",
        primary_or_secondary="PRIMARY",
        expected_path_or_url=f"{raw_path}; {processed_path}",
        available=available,
        records_count=db_summary["records_count"],
        latest_date=db_summary["latest_date"] or raw_summary["latest_year"],
        tickers_count=db_summary["tickers_count"],
        coverage_scope="acoes_e_opcoes_b3",
        status=status,
        message=message,
        metadata={"raw_summary": raw_summary, "db_summary": db_summary, "comparison": comparison},
    )

