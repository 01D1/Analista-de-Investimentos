"""Limpeza segura de tabelas operacionais com dry-run e archive."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.ops.retention_policy import get_archive_settings, get_table_retention_days, is_protected_table
from src.utils import project_path


DATE_COLUMNS = {
    "source_health_checks": "checked_at",
    "daily_routine_runs": "started_at",
    "operational_alerts": "created_at",
    "source_sla_snapshots": "created_at",
    "operational_observability_snapshots": "created_at",
    "event_coverage_runs": "created_at",
    "score_calibration_runs": "created_at",
    "historical_backtest_runs": "created_at",
    "walk_forward_runs": "created_at",
    "filter_walk_forward_runs": "created_at",
    "governance_reviews": "created_at",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone() is not None


def _cutoff(reference_date: str | datetime | None, days: int) -> str:
    reference = pd.Timestamp(reference_date) if reference_date is not None else pd.Timestamp.now()
    return (reference - pd.Timedelta(days=int(days))).date().isoformat()


def _count_old(con: sqlite3.Connection, table_name: str, date_column: str, cutoff_date: str) -> int:
    row = con.execute(f"SELECT COUNT(*) FROM {table_name} WHERE date({date_column}) < date(?)", (cutoff_date,)).fetchone()
    return int(row[0] if row else 0)


def estimate_rows_to_cleanup(db_path: str | Path, policy: dict[str, Any], reference_date: str | datetime | None = None) -> pd.DataFrame:
    columns = ["table_name", "retention_days", "cutoff_date", "rows_total", "rows_to_delete", "protected", "can_delete", "reason"]
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=columns)
    rows = []
    retention = (policy or {}).get("retention") or {}
    with sqlite3.connect(db_path) as con:
        for key in sorted(retention):
            if not key.endswith("_days"):
                continue
            table = key[:-5]
            days = get_table_retention_days(policy, table)
            protected = is_protected_table(policy, table)
            if days is None:
                continue
            cutoff = _cutoff(reference_date, days)
            special = _special_estimate(con, table, cutoff, protected)
            if special is not None:
                rows.append({"table_name": table, "retention_days": days, "cutoff_date": cutoff, "protected": protected, **special})
                continue
            if not _table_exists(con, table):
                rows.append({"table_name": table, "retention_days": days, "cutoff_date": cutoff, "rows_total": 0, "rows_to_delete": 0, "protected": protected, "can_delete": False, "reason": "Tabela ausente"})
                continue
            total = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            date_column = DATE_COLUMNS.get(table)
            if not date_column:
                rows.append({"table_name": table, "retention_days": days, "cutoff_date": cutoff, "rows_total": total, "rows_to_delete": 0, "protected": protected, "can_delete": False, "reason": "Sem coluna de data mapeada"})
                continue
            existing = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
            if date_column not in existing:
                rows.append({"table_name": table, "retention_days": days, "cutoff_date": cutoff, "rows_total": total, "rows_to_delete": 0, "protected": protected, "can_delete": False, "reason": f"Coluna ausente: {date_column}"})
                continue
            old = _count_old(con, table, date_column, cutoff)
            rows.append({"table_name": table, "retention_days": days, "cutoff_date": cutoff, "rows_total": total, "rows_to_delete": old, "protected": protected, "can_delete": bool(old and not protected), "reason": "OK" if old else "Sem linhas antigas"})
    return pd.DataFrame(rows, columns=columns)


def _archive_rows(db_path: Path, table_name: str, date_column: str, cutoff_date: str, archive_dir: str | Path) -> tuple[int, str]:
    archive_path = Path(archive_dir)
    if not archive_path.is_absolute():
        archive_path = project_path(str(archive_path))
    archive_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = archive_path / f"{table_name}_{stamp}.csv"
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} WHERE date({date_column}) < date(?)", con, params=(cutoff_date,))
    if df.empty:
        return 0, ""
    df.to_csv(out, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return int(len(df)), str(out)


def _archive_query(db_path: Path, table_name: str, sql: str, params: tuple, archive_dir: str | Path) -> tuple[int, str]:
    archive_path = Path(archive_dir)
    if not archive_path.is_absolute():
        archive_path = project_path(str(archive_path))
    archive_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = archive_path / f"{table_name}_{stamp}.csv"
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query(sql, con, params=params)
    if df.empty:
        return 0, ""
    df.to_csv(out, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return int(len(df)), str(out)


def _special_estimate(con: sqlite3.Connection, table: str, cutoff: str, protected: bool) -> dict[str, Any] | None:
    if table == "resolved_alerts":
        if not _table_exists(con, "operational_alerts"):
            return {"rows_total": 0, "rows_to_delete": 0, "can_delete": False, "reason": "Tabela operational_alerts ausente"}
        total = int(con.execute("SELECT COUNT(*) FROM operational_alerts WHERE COALESCE(resolved, 0) != 0").fetchone()[0])
        old = int(con.execute("SELECT COUNT(*) FROM operational_alerts WHERE COALESCE(resolved, 0) != 0 AND date(created_at) < date(?)", (cutoff,)).fetchone()[0])
        return {"rows_total": total, "rows_to_delete": old, "can_delete": bool(old and not protected), "reason": "OK" if old else "Sem alertas resolvidos antigos"}
    if table == "event_coverage_by_regime":
        if not _table_exists(con, "event_coverage_by_regime") or not _table_exists(con, "event_coverage_runs"):
            return {"rows_total": 0, "rows_to_delete": 0, "can_delete": False, "reason": "Tabelas de cobertura ausentes"}
        total = int(con.execute("SELECT COUNT(*) FROM event_coverage_by_regime").fetchone()[0])
        old = int(
            con.execute(
                """
                SELECT COUNT(*)
                FROM event_coverage_by_regime
                WHERE coverage_run_id IN (
                    SELECT id FROM event_coverage_runs WHERE date(created_at) < date(?)
                )
                """,
                (cutoff,),
            ).fetchone()[0]
        )
        return {"rows_total": total, "rows_to_delete": old, "can_delete": bool(old and not protected), "reason": "OK" if old else "Sem linhas antigas"}
    return None


def _cleanup_special(db_path: Path, table_name: str, cutoff_date: str, *, dry_run: bool, archive: bool, archive_dir: str | Path) -> dict[str, Any] | None:
    result = {
        "table_name": table_name,
        "cutoff_date": cutoff_date,
        "rows_total": 0,
        "rows_to_delete": 0,
        "rows_archived": 0,
        "rows_deleted": 0,
        "protected": 0,
        "status": "DRY_RUN" if dry_run else "SKIPPED",
        "archive_path": "",
        "message": "",
    }
    if table_name == "resolved_alerts":
        select_sql = "SELECT * FROM operational_alerts WHERE COALESCE(resolved, 0) != 0 AND date(created_at) < date(?)"
        delete_sql = "DELETE FROM operational_alerts WHERE COALESCE(resolved, 0) != 0 AND date(created_at) < date(?)"
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con, "operational_alerts"):
                result.update({"status": "SKIPPED", "message": "Tabela operational_alerts ausente."})
                return result
            result["rows_total"] = int(con.execute("SELECT COUNT(*) FROM operational_alerts WHERE COALESCE(resolved, 0) != 0").fetchone()[0])
            result["rows_to_delete"] = int(con.execute("SELECT COUNT(*) FROM operational_alerts WHERE COALESCE(resolved, 0) != 0 AND date(created_at) < date(?)", (cutoff_date,)).fetchone()[0])
    elif table_name == "event_coverage_by_regime":
        select_sql = """
            SELECT *
            FROM event_coverage_by_regime
            WHERE coverage_run_id IN (
                SELECT id FROM event_coverage_runs WHERE date(created_at) < date(?)
            )
        """
        delete_sql = """
            DELETE FROM event_coverage_by_regime
            WHERE coverage_run_id IN (
                SELECT id FROM event_coverage_runs WHERE date(created_at) < date(?)
            )
        """
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con, "event_coverage_by_regime") or not _table_exists(con, "event_coverage_runs"):
                result.update({"status": "SKIPPED", "message": "Tabelas de cobertura ausentes."})
                return result
            result["rows_total"] = int(con.execute("SELECT COUNT(*) FROM event_coverage_by_regime").fetchone()[0])
            result["rows_to_delete"] = int(con.execute(f"SELECT COUNT(*) FROM ({select_sql})", (cutoff_date,)).fetchone()[0])
    else:
        return None
    if result["rows_to_delete"] <= 0:
        result.update({"status": "SKIPPED", "message": "Sem linhas antigas."})
        return result
    if dry_run:
        result.update({"status": "DRY_RUN", "message": "Dry-run: nenhuma linha removida."})
        return result
    if archive:
        archived, path = _archive_query(db_path, table_name, select_sql, (cutoff_date,), archive_dir)
        result["rows_archived"] = archived
        result["archive_path"] = path
        if archived < result["rows_to_delete"]:
            result.update({"status": "ERROR", "message": "Archive incompleto; deleção bloqueada."})
            return result
    with sqlite3.connect(db_path) as con:
        cur = con.execute(delete_sql, (cutoff_date,))
        con.commit()
        result["rows_deleted"] = int(cur.rowcount or 0)
    result.update({"status": "DELETED", "message": "Linhas removidas com segurança."})
    return result


def cleanup_table(
    db_path: str | Path,
    table_name: str,
    cutoff_date: str,
    date_column: str,
    *,
    dry_run: bool = True,
    archive: bool = True,
    archive_dir: str | Path = "data/archive",
    protected_tables: set[str] | None = None,
) -> dict[str, Any]:
    db_path = Path(db_path)
    protected = table_name in (protected_tables or set())
    result = {
        "table_name": table_name,
        "cutoff_date": cutoff_date,
        "rows_total": 0,
        "rows_to_delete": 0,
        "rows_archived": 0,
        "rows_deleted": 0,
        "protected": int(protected),
        "status": "DRY_RUN" if dry_run else "SKIPPED",
        "archive_path": "",
        "message": "",
    }
    if protected:
        result.update({"status": "PROTECTED", "message": "Tabela protegida; nenhuma linha removida."})
        return result
    if not db_path.exists():
        result.update({"status": "ERROR", "message": "Banco não encontrado."})
        return result
    with sqlite3.connect(db_path) as con:
        if not _table_exists(con, table_name):
            result.update({"status": "SKIPPED", "message": "Tabela ausente."})
            return result
        result["rows_total"] = int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        result["rows_to_delete"] = _count_old(con, table_name, date_column, cutoff_date)
    if result["rows_to_delete"] <= 0:
        result.update({"status": "SKIPPED", "message": "Sem linhas antigas."})
        return result
    if dry_run:
        result.update({"status": "DRY_RUN", "message": "Dry-run: nenhuma linha removida."})
        return result
    if archive:
        archived, path = _archive_rows(db_path, table_name, date_column, cutoff_date, archive_dir)
        result["rows_archived"] = archived
        result["archive_path"] = path
        if archived < result["rows_to_delete"]:
            result.update({"status": "ERROR", "message": "Archive incompleto; deleção bloqueada."})
            return result
    with sqlite3.connect(db_path) as con:
        cur = con.execute(f"DELETE FROM {table_name} WHERE date({date_column}) < date(?)", (cutoff_date,))
        con.commit()
        result["rows_deleted"] = int(cur.rowcount or 0)
    result.update({"status": "DELETED", "message": "Linhas removidas com segurança."})
    return result


def run_retention_cleanup(
    db_path: str | Path,
    policy: dict[str, Any],
    *,
    dry_run: bool = True,
    confirm: bool = False,
    archive: bool | None = None,
    reference_date: str | datetime | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    started = _now()
    estimates = estimate_rows_to_cleanup(db_path, policy, reference_date=reference_date)
    settings = get_archive_settings(policy)
    archive_enabled = settings["enabled"] if archive is None else bool(archive)
    archive_dir = settings["dir"]
    protected_tables = set(((policy or {}).get("safety") or {}).get("never_delete_tables") or [])
    warnings: list[str] = []
    errors: list[str] = []
    details: list[dict[str, Any]] = []
    if not dry_run and not confirm:
        warnings.append("Execução real bloqueada: use --execute --confirm.")
        dry_run = True
    for _, row in estimates.iterrows():
        table = str(row["table_name"])
        date_column = DATE_COLUMNS.get(table)
        if not date_column or bool(row.get("protected")):
            special = None if bool(row.get("protected")) else _cleanup_special(Path(db_path), table, str(row["cutoff_date"]), dry_run=dry_run, archive=archive_enabled, archive_dir=archive_dir)
            if special is not None:
                details.append(special)
            else:
                details.append({**row.to_dict(), "rows_archived": 0, "rows_deleted": 0, "status": "PROTECTED" if row.get("protected") else "SKIPPED", "archive_path": "", "message": row.get("reason", "")})
            continue
        result = cleanup_table(
            db_path,
            table,
            str(row["cutoff_date"]),
            date_column,
            dry_run=dry_run,
            archive=archive_enabled,
            archive_dir=archive_dir,
            protected_tables=protected_tables,
        )
        if result["status"] == "ERROR":
            errors.append(f"{table}: {result['message']}")
        details.append(result)
    details_df = pd.DataFrame(details)
    summary = {
        "started_at": started,
        "finished_at": _now(),
        "dry_run": int(dry_run),
        "status": "FAILED" if errors else ("DRY_RUN" if dry_run else "SUCCESS"),
        "tables_evaluated": int(len(estimates)),
        "rows_candidates": int(pd.to_numeric(estimates.get("rows_to_delete"), errors="coerce").fillna(0).sum()) if not estimates.empty else 0,
        "rows_archived": int(pd.to_numeric(details_df.get("rows_archived"), errors="coerce").fillna(0).sum()) if not details_df.empty else 0,
        "rows_deleted": int(pd.to_numeric(details_df.get("rows_deleted"), errors="coerce").fillna(0).sum()) if not details_df.empty else 0,
        "archive_dir": archive_dir,
        "warnings": warnings,
        "errors": errors,
        "warnings_count": len(warnings),
        "errors_count": len(errors),
    }
    return summary, details_df
