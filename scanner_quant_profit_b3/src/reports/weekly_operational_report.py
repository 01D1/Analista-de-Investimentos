"""Relatório semanal consolidado de operação e observabilidade."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.context.source_quality_contracts import generate_contract_report
from src.notifications.alert_analytics import generate_alerts_report
from src.utils import project_path


def _pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "-"


def _table(df: pd.DataFrame, columns: list[str]) -> str:
    if df is None or df.empty:
        return "_Sem dados._"
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return "_Sem colunas esperadas._"
    return df[cols].to_markdown(index=False)


def build_weekly_operational_report(
    source_sla_df: pd.DataFrame,
    routine_summary: dict[str, Any],
    alert_summary: dict[str, Any],
    coverage_trend_df: pd.DataFrame,
    contract_df: pd.DataFrame,
    governance_reviews_df: pd.DataFrame | None = None,
) -> str:
    status = "OK"
    if alert_summary.get("critical_count", 0) or (contract_df is not None and not contract_df.empty and (contract_df["contract_status"].astype(str).str.upper() == "FAIL").any()):
        status = "CRITICAL"
    elif alert_summary.get("warning_count", 0) or routine_summary.get("routine_health_status") in {"WARNING", "CRITICAL"}:
        status = "WARNING"
    latest_coverage = coverage_trend_df.iloc[-1] if coverage_trend_df is not None and not coverage_trend_df.empty else {}
    critical_sources = []
    if source_sla_df is not None and not source_sla_df.empty:
        critical_sources = source_sla_df[source_sla_df["reliability_class"].astype(str).str.upper().eq("CRITICA")]["source_name"].astype(str).tolist()
    governance_blocked = 0
    if governance_reviews_df is not None and not governance_reviews_df.empty and "approved" in governance_reviews_df.columns:
        governance_blocked = int((pd.to_numeric(governance_reviews_df["approved"], errors="coerce").fillna(0) == 0).sum())
    actions = []
    if critical_sources:
        actions.append("Revisar fontes críticas: " + ", ".join(critical_sources))
    if not contract_df.empty and contract_df["contract_status"].astype(str).str.upper().isin(["FAIL", "WARNING"]).any():
        actions.append("Corrigir contratos de qualidade pendentes.")
    if str(latest_coverage.get("coverage_trend_direction") or "").upper() in {"PIORANDO", "INSUFICIENTE"}:
        actions.append("Ampliar cobertura de eventos antes de conclusões fortes.")
    if not actions:
        actions.append("Manter rotina diária e revisão semanal.")

    return "\n".join(
        [
            "# Relatório Semanal Operacional",
            "",
            f"Gerado em: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "## Sumário Executivo",
            "",
            f"- Status geral: **{status}**",
            f"- Fontes críticas: {len(critical_sources)}",
            f"- Cobertura recente de sinais: {_pct((latest_coverage.get('avg_signals_with_event_pct', 0) or 0) * 100)}",
            f"- Tendência de cobertura: {latest_coverage.get('coverage_trend_direction', 'INSUFICIENTE') if hasattr(latest_coverage, 'get') else 'INSUFICIENTE'}",
            f"- Rotina diária: {routine_summary.get('routine_health_status', '-')}",
            f"- Alertas abertos/total: {alert_summary.get('open_alerts', 0)}/{alert_summary.get('total_alerts', 0)}",
            f"- Reviews de governança bloqueados: {governance_blocked}",
            "",
            "## Saúde Das Fontes",
            "",
            _table(source_sla_df, ["source_name", "availability_pct", "reliability_class", "latest_status", "days_since_last_ok"]),
            "",
            "## Cobertura De Eventos",
            "",
            _table(coverage_trend_df, ["period", "avg_signals_with_event_pct", "avg_tickers_with_event_pct", "coverage_trend_direction"]),
            "",
            "## Contratos De Qualidade",
            "",
            generate_contract_report(contract_df),
            "",
            _table(contract_df, ["source_name", "contract_status", "severity", "actual_age_days", "max_age_days", "actual_records", "min_records", "actual_coverage_pct", "min_coverage_pct"]),
            "",
            "## Alertas",
            "",
            generate_alerts_report(alert_summary),
            "",
            "## Rotina Diária",
            "",
            f"- Execuções: {routine_summary.get('total_runs', 0)}",
            f"- Taxa de sucesso: {_pct(routine_summary.get('success_rate_pct', 0))}",
            f"- Taxa de falha: {_pct(routine_summary.get('failure_rate_pct', 0))}",
            f"- Média de alertas: {routine_summary.get('avg_alerts_count', 0)}",
            "",
            "## Governança",
            "",
            _table(governance_reviews_df if governance_reviews_df is not None else pd.DataFrame(), ["created_at", "candidate_name", "governance_status", "approved", "summary_text"]),
            "",
            "## Ações Recomendadas",
            "",
            "\n".join(f"- {item}" for item in actions),
            "",
            "> Relatório analítico. Não altera score, ranking, pesos, filtros ou qualquer decisão operacional.",
            "",
        ]
    )


def save_weekly_report(markdown: str, output_dir: str | Path = "data/reports") -> Path:
    out_dir = Path(output_dir)
    if not out_dir.is_absolute():
        out_dir = project_path(str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"weekly_operational_report_{datetime.now().strftime('%Y%m%d')}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
