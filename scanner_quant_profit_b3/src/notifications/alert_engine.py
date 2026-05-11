"""Geração de alertas operacionais da rotina quant."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import pandas as pd


ALERT_COLUMNS = [
    "alert_type",
    "severity",
    "title",
    "message",
    "source",
    "created_at",
    "metadata_json",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _alert(alert_type: str, severity: str, title: str, message: str, source: str = "", metadata: dict | None = None) -> dict[str, Any]:
    return {
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "source": source,
        "created_at": _now(),
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }


def _alerts_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=ALERT_COLUMNS)


def build_alerts_from_health(health_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if health_df is None or health_df.empty:
        return _alerts_df([_alert("SOURCE_EMPTY", "WARNING", "Health check vazio", "Nenhuma fonte foi avaliada.", "source_health")])
    for _, row in health_df.iterrows():
        status = str(row.get("status") or "").upper()
        source = str(row.get("source_name") or "")
        message = str(row.get("message") or "")
        if status in {"MISSING", "ERROR"}:
            rows.append(_alert("SOURCE_MISSING" if status == "MISSING" else "SOURCE_ERROR", "CRITICAL", f"{source}: {status}", message, source, row.to_dict()))
        elif status == "STALE":
            rows.append(_alert("SOURCE_STALE", "WARNING", f"{source}: fonte desatualizada", message, source, row.to_dict()))
        elif status == "EMPTY":
            rows.append(_alert("SOURCE_EMPTY", "WARNING", f"{source}: fonte vazia", message, source, row.to_dict()))
        elif status == "WARNING":
            rows.append(_alert("ROUTINE_WARNING", "WARNING", f"{source}: atenção", message, source, row.to_dict()))
    return _alerts_df(rows)


def build_alerts_from_event_coverage(coverage_summary: dict[str, Any]) -> pd.DataFrame:
    quality = str((coverage_summary or {}).get("coverage_quality") or "").upper()
    rows = []
    if quality in {"COBERTURA_FRACA", "COBERTURA_INSUFICIENTE", ""}:
        rows.append(
            _alert(
                "COVERAGE_INSUFFICIENT",
                "WARNING",
                "Cobertura de eventos insuficiente",
                f"Qualidade={quality or 'INDEFINIDA'}; sinais cobertos={(coverage_summary or {}).get('signals_with_event_pct', 0):.2%}.",
                "event_coverage",
                coverage_summary or {},
            )
        )
    return _alerts_df(rows)


def build_alerts_from_governance(governance_review: dict[str, Any] | None) -> pd.DataFrame:
    if not governance_review:
        return _alerts_df([])
    status = str(governance_review.get("governance_status") or "").upper()
    if "BLOQUEADO" not in status and not governance_review.get("approved") is False:
        return _alerts_df([])
    severity = "CRITICAL" if "OVERFITTING" in status or "LIQUIDEZ" in status else "WARNING"
    return _alerts_df(
        [
            _alert(
                "GOVERNANCE_BLOCKED",
                severity,
                f"Governança: {status}",
                governance_review.get("summary_text") or "Candidato não aprovado pela governança.",
                "governance",
                governance_review,
            )
        ]
    )


def build_daily_routine_alerts(routine_summary: dict[str, Any]) -> pd.DataFrame:
    status = str((routine_summary or {}).get("status") or "").upper()
    rows = []
    if status == "FAILED":
        rows.append(_alert("ROUTINE_FAILED", "CRITICAL", "Rotina diária falhou", str(routine_summary.get("message") or "Falha sem mensagem."), "daily_routine", routine_summary))
    elif status == "SUCCESS_WITH_WARNINGS":
        rows.append(_alert("ROUTINE_WARNING", "WARNING", "Rotina diária concluída com alertas", "Verifique health checks, cobertura e governança.", "daily_routine", routine_summary))
    return _alerts_df(rows)


def build_alerts_from_observability(observability_summary: dict[str, Any]) -> pd.DataFrame:
    summary = observability_summary or {}
    rows = []
    for source in summary.get("critical_sources_list", []) or []:
        rows.append(
            _alert(
                "SOURCE_SLA_CRITICAL",
                "CRITICAL",
                f"SLA crítico: {source}",
                "Fonte classificada como CRITICA na janela de observabilidade.",
                str(source),
                summary,
            )
        )
    for source in summary.get("unstable_sources_list", []) or []:
        rows.append(
            _alert(
                "SOURCE_SLA_UNSTABLE",
                "WARNING",
                f"SLA instável: {source}",
                "Fonte classificada como INSTAVEL ou RUIM na janela de observabilidade.",
                str(source),
                summary,
            )
        )
    if str(summary.get("routine_health_status") or "").upper() in {"CRITICAL", "NO_RUNS"}:
        rows.append(
            _alert(
                "ROUTINE_NOT_RUNNING",
                "CRITICAL",
                "Rotina diária sem saúde operacional",
                f"Status da rotina: {summary.get('routine_health_status')}. Último run: {summary.get('latest_run_at') or '-'}",
                "daily_routine",
                summary,
            )
        )
    if str(summary.get("coverage_trend_direction") or "").upper() == "PIORANDO":
        rows.append(
            _alert(
                "COVERAGE_TREND_WORSENING",
                "WARNING",
                "Cobertura de eventos piorando",
                "A tendência de cobertura de eventos caiu na janela analisada.",
                "event_coverage",
                summary,
            )
        )
    for item in summary.get("recurring_alerts", []) or []:
        rows.append(
            _alert(
                "RECURRING_ALERT",
                "WARNING",
                f"Alerta recorrente: {item.get('alert_type')}",
                f"{item.get('occurrences')} ocorrências para fonte {item.get('source')}.",
                str(item.get("source") or ""),
                item,
            )
        )
    return _alerts_df(rows)


def build_alerts_from_source_contracts(contract_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if contract_df is None or contract_df.empty:
        return _alerts_df(rows)
    for _, row in contract_df.iterrows():
        status = str(row.get("contract_status") or "").upper()
        if status not in {"FAIL", "WARNING"}:
            continue
        severity = str(row.get("severity") or ("CRITICAL" if status == "FAIL" else "WARNING")).upper()
        rows.append(
            _alert(
                "SOURCE_CONTRACT_FAILED" if status == "FAIL" else "SOURCE_CONTRACT_WARNING",
                severity if severity in {"INFO", "WARNING", "CRITICAL"} else "WARNING",
                f"Contrato de fonte: {row.get('source_name')}",
                str(row.get("message") or "Contrato de qualidade não atendido."),
                str(row.get("source_name") or ""),
                row.to_dict(),
            )
        )
    return _alerts_df(rows)


def build_alerts_from_retention_cleanup(cleanup_summary: dict[str, Any]) -> pd.DataFrame:
    summary = cleanup_summary or {}
    rows = []
    if int(summary.get("errors_count") or 0) > 0 or str(summary.get("status") or "").upper() == "FAILED":
        rows.append(
            _alert(
                "RETENTION_CLEANUP_FAILED",
                "CRITICAL",
                "Limpeza de retenção falhou",
                "; ".join(summary.get("errors") or []) or "Falha no processo de retenção.",
                "retention",
                summary,
            )
        )
    candidates = int(summary.get("rows_candidates") or 0)
    deleted = int(summary.get("rows_deleted") or 0)
    if candidates >= 10000 and deleted == 0:
        rows.append(
            _alert(
                "RETENTION_CANDIDATES_HIGH",
                "WARNING",
                "Muitas linhas candidatas à retenção",
                f"{candidates} linhas antigas foram identificadas. Revise dry-run e archive antes de executar.",
                "retention",
                summary,
            )
        )
    if int(summary.get("rows_archived") or 0) < deleted:
        rows.append(
            _alert(
                "ARCHIVE_FAILED",
                "CRITICAL",
                "Archive incompleto",
                "Linhas foram removidas sem archive equivalente registrado.",
                "retention",
                summary,
            )
        )
    return _alerts_df(rows)


def send_alerts_to_telegram(alerts_df: pd.DataFrame, config: dict | None = None) -> str:
    if alerts_df is None or alerts_df.empty:
        return "Sem alertas para enviar."
    token = os.getenv("TELEGRAM_BOT_TOKEN") or (config or {}).get("telegram_bot_token")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or (config or {}).get("telegram_chat_id")
    if not token or not chat_id:
        return "Telegram não configurado"
    text = "\n\n".join(
        f"[{row.get('severity')}] {row.get('title')}\n{row.get('message')}"
        for _, row in alerts_df.head(10).iterrows()
    )
    try:
        import requests

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
        if response.ok and response.json().get("ok"):
            return "Alertas enviados ao Telegram."
        return f"Falha no Telegram: HTTP {response.status_code}"
    except Exception as exc:
        return f"Falha no Telegram: {exc}"
