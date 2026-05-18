"""Executor seguro do plano de ingestao."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from src.data_quality.ingestion_plan import INGESTION_STEP_COLUMNS
from src.utils import project_path


WHITELIST = [
    "python -m src.collectors.b3_cotahist_collector --year",
    "python -m src.scanners.realtime_profit_scanner --once",
    "python -m src.scanners.options_history_builder",
    "python -m src.scanners.options_intelligence_scanner",
    "python -m src.scanners.data_reconciliation",
    "python -m src.scanners.data_source_audit",
]


def _is_whitelisted(command: str) -> bool:
    command = " ".join(str(command).strip().split())
    return any(command.startswith(prefix) for prefix in WHITELIST)


def _argv(command: str) -> list[str]:
    parts = command.split()
    if parts and parts[0].lower() == "python":
        parts[0] = sys.executable
    return parts


def execute_ingestion_step(step: dict | pd.Series, dry_run: bool = True, confirm: bool = False, timeout: int = 900) -> dict:
    row = step.to_dict() if hasattr(step, "to_dict") else dict(step)
    command = str(row.get("suggested_command") or "").strip()
    if not bool(row.get("can_execute")):
        status = "MANUAL_REQUIRED"
        return {**row, "status": status, "stdout": "", "stderr": "Etapa manual ou sem comando executavel."}
    if dry_run:
        return {**row, "status": "DRY_RUN", "stdout": "", "stderr": ""}
    if bool(row.get("requires_confirm")) and not confirm:
        return {**row, "status": "BLOCKED_CONFIRMATION_REQUIRED", "stdout": "", "stderr": "Use --execute --confirm para executar."}
    if not _is_whitelisted(command):
        return {**row, "status": "BLOCKED_NOT_WHITELISTED", "stdout": "", "stderr": "Comando fora da whitelist."}
    try:
        proc = subprocess.run(_argv(command), cwd=project_path("."), capture_output=True, text=True, timeout=timeout)
        return {**row, "status": "SUCCESS" if proc.returncode == 0 else "FAILED", "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    except Exception as exc:
        return {**row, "status": "FAILED", "stdout": "", "stderr": str(exc)}


def execute_ingestion_plan(plan_df: pd.DataFrame, dry_run: bool = True, confirm: bool = False, only_sources: list[str] | None = None) -> pd.DataFrame:
    if plan_df is None or plan_df.empty:
        return pd.DataFrame(columns=[*INGESTION_STEP_COLUMNS, "stdout", "stderr"])
    work = plan_df.copy().sort_values("step_order")
    if only_sources:
        aliases = {"PROFIT": "PROFIT_RTD", "B3_COTAHIST": "B3"}
        allowed = {aliases.get(s.upper(), s.upper()) for s in only_sources}
        work = work[work["source_domain"].astype(str).str.upper().isin(allowed)]
    rows = []
    failed_sources: set[str] = set()
    for _, step in work.iterrows():
        source = str(step.get("source_domain") or "").upper()
        if source in failed_sources:
            rows.append({**step.to_dict(), "status": "SKIPPED", "stdout": "", "stderr": "Etapa dependente ignorada apos falha anterior."})
            continue
        result = execute_ingestion_step(step, dry_run=dry_run, confirm=confirm)
        rows.append(result)
        if result["status"] == "FAILED":
            failed_sources.add(source)
    return pd.DataFrame(rows)
