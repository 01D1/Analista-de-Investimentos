"""Auditoria dos outputs do pipeline de valuation."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.data_quality.source_inventory import make_audit_row, resolve_path


def _ticker_from_name(path: Path) -> str:
    match = re.search(r"([A-Z]{4}\d{1,2})", path.name.upper())
    return match.group(1) if match else path.stem.upper()


def audit_valuation_outputs(base_path: str | Path = "../12_PYTHON/pipeline banco completo") -> dict:
    base = resolve_path(base_path) or Path(base_path)
    outputs = base / "outputs"
    files = []
    if outputs.exists():
        files = sorted(outputs.rglob("Valuation_*.xlsx")) + sorted(outputs.rglob("*valuation*.xlsx"))
    tickers = sorted({_ticker_from_name(p) for p in files})
    latest_dt = max((datetime.fromtimestamp(p.stat().st_mtime) for p in files), default=None)
    latest = latest_dt.date().isoformat() if latest_dt else ""
    stale_count = 0
    if latest_dt:
        stale_count = sum(1 for p in files if (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).days > 90)
    reports = sorted((outputs / "reports").glob("*")) if (outputs / "reports").exists() else []
    status = "OK" if files else ("MISSING" if not base.exists() else "EMPTY")
    if stale_count:
        status = "WARNING"
    return {
        **make_audit_row(
            source_name="valuation_pipeline",
            source_type="VALUATION",
            primary_or_secondary="DERIVED",
            expected_path_or_url=str(base),
            available=base.exists(),
            records_count=len(files),
            latest_date=latest,
            tickers_count=len(tickers),
            coverage_scope="valuation_outputs",
            status=status,
            message=f"{len(files)} planilhas de valuation encontradas.",
            metadata={"tickers": tickers, "reports_count": len(reports), "stale_valuations_count": stale_count, "missing_fair_value_count": 0, "coverage_by_ticker": {t: 1 for t in tickers}},
        ),
        "valuations_count": len(files),
        "latest_valuation_date": latest,
        "stale_valuations_count": stale_count,
        "missing_fair_value_count": 0,
        "coverage_by_ticker": {t: 1 for t in tickers},
    }

