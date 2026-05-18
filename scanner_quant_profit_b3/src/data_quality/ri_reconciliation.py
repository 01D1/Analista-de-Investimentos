"""Reconcilia URLs de RI configuradas em empresas.yaml."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_quality.ri_audit import load_ri_urls
from src.data_quality.source_inventory import resolve_path


def detect_missing_ri_urls(empresas_yaml: str | Path | None = None) -> pd.DataFrame:
    df = load_ri_urls(empresas_yaml=empresas_yaml)
    columns = ["ticker", "company_name", "has_ri_url", "ri_url", "missing_reason"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for _, row in df.iterrows():
        url = str(row.get("ri_url") or "").strip()
        rows.append(
            {
                "ticker": str(row.get("ticker") or "").upper(),
                "company_name": row.get("company_name", ""),
                "has_ri_url": bool(url),
                "ri_url": url,
                "missing_reason": "" if url else "URL de RI ausente em empresas.yaml.",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def suggest_ri_url_template(ticker: str, company_name: str = "") -> str:
    label = f" # {company_name}" if company_name else ""
    return f"{ticker}:\n  nome: \"{company_name or ticker}\"\n  ri_url: \"PREENCHER_URL_RI\"{label}"

