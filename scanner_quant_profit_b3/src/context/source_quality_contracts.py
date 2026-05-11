"""Contratos de qualidade por fonte de dados."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.utils import project_path


CONTRACT_COLUMNS = [
    "source_name",
    "contract_status",
    "required",
    "severity",
    "checks_passed",
    "checks_failed",
    "max_age_days",
    "actual_age_days",
    "min_records",
    "actual_records",
    "min_coverage_pct",
    "actual_coverage_pct",
    "message",
]


def load_source_quality_contracts(path: str | Path = "config/source_quality_contracts.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = project_path(str(config_path))
    if not config_path.exists():
        return {"sources": {}}
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"sources": {}}


def _latest_health(health_df: pd.DataFrame) -> pd.DataFrame:
    if health_df is None or health_df.empty or "source_name" not in health_df.columns:
        return pd.DataFrame()
    df = health_df.copy()
    df["checked_at_dt"] = pd.to_datetime(df.get("checked_at"), errors="coerce")
    return df.sort_values("checked_at_dt").groupby("source_name", dropna=False).tail(1)


def _coverage_for_source(coverage_df: pd.DataFrame | None, source: str) -> float | None:
    if coverage_df is None or coverage_df.empty:
        return None
    df = coverage_df.copy()
    if "created_at" in df.columns:
        df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.sort_values("created_at_dt")
    latest = df.tail(1)
    if latest.empty:
        return None
    sources = str(latest.iloc[0].get("sources") or "")
    if source not in [part.strip() for part in sources.split(",") if part.strip()]:
        return 0.0
    value = pd.to_numeric(pd.Series([latest.iloc[0].get("signals_with_event_pct")]), errors="coerce").iloc[0]
    if pd.isna(value):
        return None
    return float(value) * 100 if value <= 1 else float(value)


def evaluate_source_contracts(health_df: pd.DataFrame, coverage_df: pd.DataFrame | None = None, contracts: dict[str, Any] | None = None) -> pd.DataFrame:
    contracts = contracts or {"sources": {}}
    sources = contracts.get("sources") or {}
    latest = _latest_health(health_df)
    rows = []
    if not sources:
        return pd.DataFrame(columns=CONTRACT_COLUMNS)
    for source, contract in sources.items():
        row = latest[latest["source_name"].astype(str) == str(source)] if not latest.empty else pd.DataFrame()
        required = bool(contract.get("required", False))
        severity = str(contract.get("severity_if_fail", "WARNING")).upper()
        max_age = contract.get("max_age_days")
        min_records = contract.get("min_records")
        min_coverage = contract.get("min_coverage_pct")
        actual_age = None
        actual_records = None
        actual_coverage = _coverage_for_source(coverage_df, str(source)) if min_coverage is not None else None
        failures = []
        passed = []
        if row.empty:
            if required:
                failures.append("fonte sem health check")
            else:
                rows.append(
                    {
                        "source_name": source,
                        "contract_status": "NOT_APPLICABLE",
                        "required": required,
                        "severity": severity,
                        "checks_passed": 0,
                        "checks_failed": 0,
                        "max_age_days": max_age,
                        "actual_age_days": actual_age,
                        "min_records": min_records,
                        "actual_records": actual_records,
                        "min_coverage_pct": min_coverage,
                        "actual_coverage_pct": actual_coverage,
                        "message": "Fonte opcional sem health check.",
                    }
                )
                continue
        else:
            h = row.iloc[0]
            actual_age = pd.to_numeric(pd.Series([h.get("age_days")]), errors="coerce").iloc[0]
            actual_records = pd.to_numeric(pd.Series([h.get("records_count")]), errors="coerce").iloc[0]
            status = str(h.get("status") or "").upper()
            if status in {"ERROR", "MISSING", "EMPTY"}:
                failures.append(f"status={status}")
            else:
                passed.append("status")
            if max_age is not None and pd.notna(actual_age):
                (passed if float(actual_age) <= float(max_age) else failures).append("idade")
            if min_records is not None and pd.notna(actual_records):
                (passed if float(actual_records) >= float(min_records) else failures).append("registros")
        if min_coverage is not None and actual_coverage is not None:
            (passed if actual_coverage >= float(min_coverage) else failures).append("cobertura")
        if failures:
            status = "FAIL" if severity == "CRITICAL" or required else "WARNING"
        else:
            status = "PASS"
        rows.append(
            {
                "source_name": source,
                "contract_status": status,
                "required": required,
                "severity": severity,
                "checks_passed": len(passed),
                "checks_failed": len(failures),
                "max_age_days": max_age,
                "actual_age_days": None if pd.isna(actual_age) else actual_age,
                "min_records": min_records,
                "actual_records": None if pd.isna(actual_records) else actual_records,
                "min_coverage_pct": min_coverage,
                "actual_coverage_pct": actual_coverage,
                "message": "PASS" if not failures else "Falhas: " + ", ".join(failures),
            }
        )
    return pd.DataFrame(rows, columns=CONTRACT_COLUMNS)


def generate_contract_report(contract_df: pd.DataFrame) -> str:
    if contract_df is None or contract_df.empty:
        return "Nenhum contrato de qualidade foi avaliado."
    failed = contract_df[contract_df["contract_status"].astype(str).str.upper().isin(["FAIL", "WARNING"])]
    if failed.empty:
        return f"Contratos de qualidade aprovados para {len(contract_df)} fontes avaliadas."
    labels = (failed["source_name"].astype(str) + "=" + failed["contract_status"].astype(str)).tolist()
    return "Contratos com atenção: " + ", ".join(labels) + "."
