"""Reconcilia freshness do Profit RTD com snapshots no SQLite."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from src.data_quality.profit_rtd_audit import audit_profit_excel
from src.data_quality.source_inventory import resolve_path, table_exists
from src.utils import load_config, project_path


def _age_hours(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(str(value)[:19])).total_seconds() / 3600
    except Exception:
        return None


def check_profit_freshness(config_path: str | Path = "config.yaml") -> dict:
    cfg = load_config() if str(config_path) == "config.yaml" else {}
    audit = audit_profit_excel(config_path)
    db_path = project_path(cfg.get("database_path", "data/database/scanner_quant.db")) if cfg else None
    latest_snapshot = ""
    snapshots_count = 0
    if db_path and db_path.exists():
        try:
            with sqlite3.connect(db_path) as con:
                if table_exists(con, "profit_snapshots"):
                    snapshots_count, latest_snapshot = con.execute("SELECT COUNT(*), MAX(captured_at) FROM profit_snapshots").fetchone()
        except Exception:
            pass
    excel_age = None
    path = resolve_path(cfg.get("profit_excel_path")) if cfg else None
    if path and path.exists():
        excel_age = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).total_seconds() / 3600
    snapshot_age = _age_hours(latest_snapshot)
    stale = bool((excel_age is not None and excel_age > 24) or (snapshot_age is None or snapshot_age > 24))
    status = "STALE" if stale else "OK"
    if audit.get("status") in {"MISSING", "ERROR"}:
        status = audit.get("status")
    return {
        "status": status,
        "excel_status": audit.get("status"),
        "excel_path": audit.get("expected_path_or_url", ""),
        "excel_modified_at": audit.get("latest_date", ""),
        "excel_age_hours": excel_age,
        "snapshots_count": int(snapshots_count or 0),
        "latest_snapshot_at": latest_snapshot or "",
        "snapshot_age_hours": snapshot_age,
        "message": "Profit RTD esta stale ou sem leitura recente." if stale else "Profit RTD com leitura recente.",
    }


def suggest_profit_actions(audit_result: dict) -> list[str]:
    actions = [
        "Abrir o Profit e confirmar RTD ativo.",
        "Abrir o Excel RTD configurado em config.yaml.",
        "Confirmar profit_excel_path e profit_sheet_name em config.yaml.",
        "python -m src.scanners.realtime_profit_scanner --once --save-db",
        "python -m src.scanners.realtime_profit_scanner --once --demo",
    ]
    if audit_result.get("status") == "OK":
        return []
    return actions

