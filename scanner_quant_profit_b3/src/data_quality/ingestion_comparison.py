"""Comparacao de confiabilidade antes/depois da ingestao."""
from __future__ import annotations

import pandas as pd


COMPARISON_COLUMNS = ["source_name", "before_score", "after_score", "score_delta", "before_status", "after_status", "status_improved", "records_delta", "freshness_improved", "message", "metadata_json"]


def compare_reliability_before_after(before_audit_df: pd.DataFrame, after_audit_df: pd.DataFrame) -> pd.DataFrame:
    before = before_audit_df if before_audit_df is not None else pd.DataFrame()
    after = after_audit_df if after_audit_df is not None else pd.DataFrame()
    if before.empty and after.empty:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)
    rows = []
    names = sorted(set(before.get("source_name", pd.Series(dtype=str)).dropna().astype(str)) | set(after.get("source_name", pd.Series(dtype=str)).dropna().astype(str)))
    good = {"OK", "CONFIAVEL", "ACEITAVEL"}
    for name in names:
        b = before[before["source_name"].astype(str) == name].iloc[0] if not before.empty and (before["source_name"].astype(str) == name).any() else {}
        a = after[after["source_name"].astype(str) == name].iloc[0] if not after.empty and (after["source_name"].astype(str) == name).any() else {}
        before_score = float(getattr(b, "get", lambda *_: 0)("reliability_score", 0) or 0)
        after_score = float(getattr(a, "get", lambda *_: 0)("reliability_score", 0) or 0)
        before_status = str(getattr(b, "get", lambda *_: "")("status", ""))
        after_status = str(getattr(a, "get", lambda *_: "")("status", ""))
        records_delta = int(getattr(a, "get", lambda *_: 0)("records_count", 0) or 0) - int(getattr(b, "get", lambda *_: 0)("records_count", 0) or 0)
        rows.append(
            {
                "source_name": name,
                "before_score": before_score,
                "after_score": after_score,
                "score_delta": round(after_score - before_score, 2),
                "before_status": before_status,
                "after_status": after_status,
                "status_improved": after_status in good and before_status not in good,
                "records_delta": records_delta,
                "freshness_improved": str(getattr(a, "get", lambda *_: "")("latest_date", "")) > str(getattr(b, "get", lambda *_: "")("latest_date", "")),
                "message": f"{name}: score {before_score:.1f} -> {after_score:.1f}; status {before_status} -> {after_status}.",
                "metadata_json": "{}",
            }
        )
    return pd.DataFrame(rows, columns=COMPARISON_COLUMNS)


def generate_ingestion_comparison_report(comparison_df: pd.DataFrame) -> str:
    if comparison_df is None or comparison_df.empty:
        return "Sem comparacao antes/depois disponivel."
    lines = []
    for _, row in comparison_df.iterrows():
        lines.append(row.get("message", ""))
    return "\n".join(lines)

