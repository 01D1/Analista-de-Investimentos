"""Auditoria de indices CVM/IPE locais."""
from __future__ import annotations

import json
from pathlib import Path

from src.data_quality.source_inventory import make_audit_row, resolve_path


def _as_docs(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ["documents", "docs", "items", "eventos", "records"]:
            if isinstance(payload.get(key), list):
                return payload[key]
        return [payload]
    return []


def audit_cvm_ipe(base_dir: str | Path = "../12_PYTHON/pipeline banco completo/data/qualitative/processed") -> dict:
    base = resolve_path(base_dir) or Path(base_dir)
    files = sorted(base.glob("*/cvm_ipe_index.json")) if base.exists() else []
    tickers: set[str] = set()
    categories: set[str] = set()
    docs_count = 0
    latest = ""
    missing_links = 0
    empty_docs = 0
    coverage: dict[str, int] = {}
    for file in files:
        ticker = file.parent.name.upper()
        tickers.add(ticker)
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
            docs = _as_docs(payload)
            coverage[ticker] = len(docs)
            docs_count += len(docs)
            for doc in docs:
                if not isinstance(doc, dict):
                    continue
                categories.add(str(doc.get("categoria") or doc.get("category") or doc.get("tipo") or ""))
                date = str(doc.get("data") or doc.get("date") or doc.get("reference_date") or "")
                if date and date > latest:
                    latest = date[:10]
                link = doc.get("link") or doc.get("url") or doc.get("download_url")
                if not link:
                    missing_links += 1
                local = doc.get("local_path") or doc.get("file_path")
                if local and Path(local).exists() and Path(local).stat().st_size == 0:
                    empty_docs += 1
        except Exception:
            empty_docs += 1
    status = "OK" if docs_count else ("MISSING" if not files else "EMPTY")
    if missing_links and docs_count:
        status = "WARNING"
    return {
        **make_audit_row(
            source_name="cvm_ipe",
            source_type="REGULATORY",
            primary_or_secondary="PRIMARY",
            expected_path_or_url=str(base),
            available=bool(files),
            records_count=docs_count,
            latest_date=latest,
            tickers_count=len(tickers),
            coverage_scope="documentos_cvm_ipe",
            status=status,
            message=f"{len(files)} indices CVM/IPE encontrados; {docs_count} documentos mapeados.",
            metadata={"tickers": sorted(tickers), "categories": sorted(c for c in categories if c), "coverage_by_ticker": coverage, "missing_links_count": missing_links, "empty_docs_count": empty_docs},
        ),
        "tickers_count": len(tickers),
        "docs_count": docs_count,
        "latest_doc_date": latest,
        "missing_links_count": missing_links,
        "empty_docs_count": empty_docs,
        "coverage_by_ticker": coverage,
    }

