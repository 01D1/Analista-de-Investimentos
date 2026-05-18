"""Score de confiabilidade das fontes auditadas."""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def _parse_date(value) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
    except Exception:
        return None


def _freshness_score(latest_date) -> float:
    dt = _parse_date(latest_date)
    if dt is None:
        return 30.0
    age = (datetime.now() - dt.replace(tzinfo=None)).days
    if age <= 7:
        return 100.0
    if age <= 30:
        return 75.0
    if age <= 90:
        return 50.0
    return 20.0


def _class(score: float) -> str:
    if score >= 80:
        return "CONFIAVEL"
    if score >= 60:
        return "ACEITAVEL"
    if score >= 40:
        return "FRAGIL"
    if score > 0:
        return "INSUFICIENTE"
    return "INDISPONIVEL"


def calculate_source_reliability_score(audit_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df is None or audit_df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in audit_df.iterrows():
        status = str(row.get("status", "")).upper()
        available = bool(row.get("available")) and status not in {"MISSING", "ERROR"}
        records = float(row.get("records_count") or 0)
        tickers = float(row.get("tickers_count") or 0)
        availability_score = 100.0 if available else 0.0
        freshness_score = _freshness_score(row.get("latest_date"))
        completeness_score = 100.0 if records > 0 and tickers > 0 else (70.0 if records > 0 else 0.0)
        traceability_score = 100.0 if str(row.get("expected_path_or_url", "")).strip() else 40.0
        origin = str(row.get("primary_or_secondary", "")).upper()
        primary_source_score = {"PRIMARY": 100.0, "SECONDARY": 75.0, "DERIVED": 60.0, "MANUAL": 55.0}.get(origin, 40.0)
        consistency_score = 100.0
        if status in {"WARNING", "STALE", "EMPTY", "NOT_CHECKED"}:
            consistency_score = 60.0
        if status in {"ERROR", "MISSING"}:
            consistency_score = 0.0
        score = round(
            availability_score * 0.25
            + freshness_score * 0.20
            + completeness_score * 0.20
            + traceability_score * 0.15
            + primary_source_score * 0.10
            + consistency_score * 0.10,
            2,
        )
        out = row.to_dict()
        out.update(
            {
                "availability_score": availability_score,
                "freshness_score": freshness_score,
                "completeness_score": completeness_score,
                "traceability_score": traceability_score,
                "primary_source_score": primary_source_score,
                "consistency_score": consistency_score,
                "reliability_score": score,
                "reliability_class": _class(score),
            }
        )
        rows.append(out)
    return pd.DataFrame(rows)


def generate_source_reliability_report(reliability_df: pd.DataFrame) -> str:
    if reliability_df is None or reliability_df.empty:
        return "Sem dados de auditoria suficientes para calcular confiabilidade."
    lines = []
    for _, row in reliability_df.iterrows():
        lines.append(
            f"{row.get('source_name')} esta com status {row.get('status')} e score "
            f"{row.get('reliability_score'):.1f}. Classificacao: {row.get('reliability_class')}."
        )
    return "\n".join(lines)
