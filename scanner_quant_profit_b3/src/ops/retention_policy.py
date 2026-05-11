"""Políticas de retenção e regras de segurança para limpeza operacional."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.utils import project_path


DEFAULT_POLICY: dict[str, Any] = {
    "retention": {
        "source_health_checks_days": 180,
        "daily_routine_runs_days": 365,
        "operational_alerts_days": 365,
        "resolved_alerts_days": 180,
        "source_sla_snapshots_days": 365,
        "operational_observability_snapshots_days": 365,
        "event_coverage_runs_days": 365,
        "event_coverage_by_regime_days": 365,
        "score_calibration_runs_days": 365,
        "historical_backtest_runs_days": 730,
        "walk_forward_runs_days": 730,
        "filter_walk_forward_runs_days": 730,
        "governance_reviews_days": 730,
    },
    "archive": {"enabled": True, "dir": "data/archive", "format": "csv"},
    "safety": {
        "dry_run_default": True,
        "require_confirm_for_delete": True,
        "never_delete_tables": ["market_daily", "b3_quotes", "historical_backtest_results", "market_events"],
    },
}


def load_retention_policy(config_path: str | Path = "config/retention.yaml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.is_absolute():
        path = project_path(str(path))
    if not path.exists():
        return DEFAULT_POLICY.copy()
    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    policy = DEFAULT_POLICY.copy()
    for section in ["retention", "archive", "safety"]:
        policy[section] = {**DEFAULT_POLICY.get(section, {}), **(loaded.get(section) or {})}
    return policy


def _key(table_name: str) -> str:
    return f"{table_name}_days"


def get_table_retention_days(policy: dict[str, Any], table_name: str) -> int | None:
    value = (policy or {}).get("retention", {}).get(_key(table_name))
    if value is None:
        return None
    return int(value)


def get_archive_settings(policy: dict[str, Any]) -> dict[str, Any]:
    archive = (policy or {}).get("archive") or {}
    return {
        "enabled": bool(archive.get("enabled", True)),
        "dir": archive.get("dir", "data/archive"),
        "format": archive.get("format", "csv"),
    }


def validate_retention_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    retention = (policy or {}).get("retention") or {}
    for name, value in retention.items():
        try:
            days = int(value)
        except (TypeError, ValueError):
            errors.append(f"{name}: valor de retenção inválido")
            continue
        if days < 0:
            errors.append(f"{name}: retenção negativa não permitida")
    protected = set(((policy or {}).get("safety") or {}).get("never_delete_tables") or [])
    for key in retention:
        table = key[:-5] if key.endswith("_days") else key
        if table in protected:
            errors.append(f"{table}: tabela protegida não pode ter política de deleção")
    return errors


def is_protected_table(policy: dict[str, Any], table_name: str) -> bool:
    protected = set(((policy or {}).get("safety") or {}).get("never_delete_tables") or [])
    return table_name in protected
