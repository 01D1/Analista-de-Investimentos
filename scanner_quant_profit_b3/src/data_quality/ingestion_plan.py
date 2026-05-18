"""Plano operacional guiado para ingestao de dados."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


INGESTION_STEP_COLUMNS = [
    "step_id",
    "step_order",
    "source_domain",
    "step_type",
    "title",
    "description",
    "suggested_command",
    "can_execute",
    "requires_confirm",
    "risk_level",
    "expected_outputs",
    "validation_checks",
    "status",
    "metadata_json",
]


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _step(order: int, domain: str, step_type: str, title: str, description: str, command: str = "", can_execute: bool = False, risk: str = "LOW", checks: list[str] | None = None, metadata: dict | None = None) -> dict:
    return {
        "step_id": f"{domain}_{order:03d}",
        "step_order": order,
        "source_domain": domain,
        "step_type": step_type,
        "title": title,
        "description": description,
        "suggested_command": command,
        "can_execute": bool(can_execute and command),
        "requires_confirm": bool(can_execute and command),
        "risk_level": risk,
        "expected_outputs": _json(metadata.get("expected_outputs") if metadata else []),
        "validation_checks": _json(checks or []),
        "status": "PLANNED",
        "metadata_json": _json(metadata),
    }


def build_ingestion_plan_from_reconciliation(reconciliation_df: pd.DataFrame) -> pd.DataFrame:
    if reconciliation_df is None or reconciliation_df.empty:
        return pd.DataFrame(columns=INGESTION_STEP_COLUMNS)
    steps: list[dict] = []
    order = 1
    for _, row in reconciliation_df.iterrows():
        issue = str(row.get("issue_type") or "")
        domain = str(row.get("source_domain") or "").upper()
        command = str(row.get("suggested_command") or "").strip()
        if issue == "OK":
            continue
        if domain == "B3_COTAHIST" and issue == "OPTIONS_MISSING":
            steps.append(_step(order, "OPTIONS", "PROCESS", "Construir histórico de opções a partir da B3", row.get("description", ""), command, True, "MEDIUM", ["validate_options_after_ingestion"], {"issue_type": issue}))
        elif domain == "B3_COTAHIST":
            steps.append(_step(order, "B3", "PROCESS", "Reprocessar COTAHIST B3", row.get("description", ""), command, True, "MEDIUM", ["validate_b3_after_ingestion"], {"issue_type": issue}))
        elif domain == "PROFIT_RTD":
            steps.append(_step(order, "PROFIT_RTD", "MANUAL_ACTION", "Atualizar Profit RTD/Excel", "Abrir Profit e Excel RTD antes de nova leitura.", "", False, "LOW", ["validate_profit_after_ingestion"], {"issue_type": issue}))
            order += 1
            steps.append(_step(order, "PROFIT_RTD", "PROCESS", "Capturar snapshot Profit", row.get("description", ""), command, True, "LOW", ["validate_profit_after_ingestion"], {"issue_type": issue}))
        elif domain == "OPTIONS":
            step_type = "PROCESS" if command else "CHECK"
            steps.append(_step(order, "OPTIONS", step_type, "Construir/atualizar dados de opções", row.get("description", ""), command, bool(command), "MEDIUM", ["validate_options_after_ingestion"], {"issue_type": issue}))
        elif domain == "RI":
            steps.append(_step(order, "RI", "CONFIGURE", "Preencher URL de RI", row.get("description", ""), "", False, "LOW", ["validate_ri_after_configuration"], {"issue_type": issue, "template": row.get("metadata_json", "")}))
        else:
            steps.append(_step(order, domain or "UNKNOWN", "CHECK", "Revisar reconciliação", row.get("description", ""), command, bool(command), "LOW", [], {"issue_type": issue}))
        order += 1
    return pd.DataFrame(steps, columns=INGESTION_STEP_COLUMNS)


def summarize_ingestion_plan(plan_df: pd.DataFrame) -> dict:
    if plan_df is None or plan_df.empty:
        return {"total_steps": 0, "executable_steps": 0, "manual_steps": 0, "high_risk_steps": 0, "sources_covered": "", "status": "EMPTY"}
    executable = int(plan_df["can_execute"].fillna(False).astype(bool).sum())
    manual = int((~plan_df["can_execute"].fillna(False).astype(bool)).sum())
    high = int(plan_df["risk_level"].astype(str).str.upper().eq("HIGH").sum())
    sources = sorted(plan_df["source_domain"].dropna().astype(str).unique().tolist())
    return {
        "total_steps": int(len(plan_df)),
        "executable_steps": executable,
        "manual_steps": manual,
        "high_risk_steps": high,
        "sources_covered": ",".join(sources),
        "status": "READY" if executable or manual else "EMPTY",
    }
