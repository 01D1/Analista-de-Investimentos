"""Validacao apos etapas de ingestao."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.data_quality.b3_reconciliation import summarize_b3_sqlite
from src.data_quality.options_reconciliation import summarize_options_sources
from src.data_quality.profit_reconciliation import check_profit_freshness
from src.data_quality.ri_reconciliation import detect_missing_ri_urls
from src.utils import load_config, project_path


VALIDATION_COLUMNS = ["source_domain", "validation_status", "before_status", "after_status", "improvement_detected", "records_before", "records_after", "latest_date_before", "latest_date_after", "message", "metadata_json"]


def _row(domain: str, status: str, records: int, latest: str, message: str, metadata: dict | None = None, before: dict | None = None) -> dict:
    before = before or {}
    return {
        "source_domain": domain,
        "validation_status": status,
        "before_status": before.get("status", ""),
        "after_status": status,
        "improvement_detected": bool(records > int(before.get("records", 0) or 0) or (before.get("status") and before.get("status") != status and status == "OK")),
        "records_before": int(before.get("records", 0) or 0),
        "records_after": int(records or 0),
        "latest_date_before": before.get("latest_date", ""),
        "latest_date_after": latest or "",
        "message": message,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }


def validate_b3_after_ingestion(db_path: str | Path, expected_years: list[str] | None = None, before: dict | None = None) -> dict:
    summary = summarize_b3_sqlite(db_path)
    rows = int(summary["rows_count"].fillna(0).sum()) if not summary.empty else 0
    latest = str(summary["latest_date"].max()) if not summary.empty and "latest_date" in summary.columns else ""
    years = set()
    for value in summary.get("years_available", pd.Series(dtype=str)).fillna(""):
        years.update(y for y in str(value).split(",") if y)
    missing = sorted(set(str(y) for y in (expected_years or [])) - years)
    status = "OK" if rows > 0 and not missing else ("WARNING" if rows > 0 else "FAILED")
    return _row("B3", status, rows, latest, "B3 validada apos ingestao." if status == "OK" else "B3 ainda possui lacunas.", {"years_available": sorted(years), "missing_years": missing, "summary": summary.to_dict(orient="records")}, before)


def validate_profit_after_ingestion(db_path: str | Path, config_path: str | Path | None = None, before: dict | None = None) -> dict:
    audit = check_profit_freshness(config_path or "config.yaml")
    status = "OK" if audit.get("status") == "OK" else "STALE"
    return _row("PROFIT_RTD", status, int(audit.get("snapshots_count") or 0), audit.get("latest_snapshot_at", ""), audit.get("message", ""), audit, before)


def validate_options_after_ingestion(db_path: str | Path, underlyings: list[str] | None = None, before: dict | None = None) -> dict:
    summary = summarize_options_sources(db_path)
    missing = sorted(set(u.upper() for u in (underlyings or [])) - set(str(u).upper() for u in summary.get("underlyings", [])))
    status = "OK" if summary.get("snapshots_count", 0) > 0 and not missing else "FAILED"
    return _row("OPTIONS", status, int(summary.get("snapshots_count") or 0), summary.get("latest_snapshot_date", ""), "Opcoes validadas." if status == "OK" else "Cadeia de opcoes ainda insuficiente.", {"missing_underlyings": missing, **summary}, before)


def validate_ri_after_configuration(empresas_yaml: str | Path | None = None, before: dict | None = None) -> dict:
    df = detect_missing_ri_urls(empresas_yaml)
    missing = int((~df["has_ri_url"].fillna(False).astype(bool)).sum()) if not df.empty else 0
    status = "OK" if not missing and not df.empty else "WARNING"
    return _row("RI", status, int(len(df) - missing), "", f"{missing} empresas sem URL de RI." if missing else "URLs de RI configuradas.", {"missing_count": missing}, before)


def run_post_ingestion_validation(sources: list[str], db_path: str | Path | None = None, before_map: dict | None = None) -> pd.DataFrame:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    selected = {s.lower() for s in sources}
    if "all" in selected:
        selected = {"b3", "profit", "options", "ri"}
    rows = []
    before_map = before_map or {}
    if "b3" in selected:
        rows.append(validate_b3_after_ingestion(db, before=before_map.get("B3")))
    if "profit" in selected:
        rows.append(validate_profit_after_ingestion(db, before=before_map.get("PROFIT_RTD")))
    if "options" in selected:
        rows.append(validate_options_after_ingestion(db, cfg.get("ativos_base", []), before=before_map.get("OPTIONS")))
    if "ri" in selected:
        rows.append(validate_ri_after_configuration(before=before_map.get("RI")))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)

