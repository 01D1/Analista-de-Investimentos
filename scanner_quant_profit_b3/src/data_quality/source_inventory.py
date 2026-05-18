"""Inventario consolidado das fontes criticas de dados."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils import project_path


AUDIT_RESULT_COLUMNS = [
    "source_name",
    "source_type",
    "primary_or_secondary",
    "expected_path_or_url",
    "available",
    "records_count",
    "latest_date",
    "tickers_count",
    "coverage_scope",
    "last_checked_at",
    "status",
    "message",
    "metadata_json",
]

TRACEABILITY_COLUMNS = [
    "created_at",
    "ticker",
    "data_domain",
    "source_name",
    "source_type",
    "source_url_or_path",
    "source_date",
    "collected_at",
    "record_count",
    "checksum",
    "metadata_json",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def to_json(value: Any) -> str:
    try:
        return json.dumps(value or {}, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def resolve_path(path: str | Path | None) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    if str(path).startswith(".."):
        return (project_path(".") / p).resolve()
    return project_path(str(path))


def table_exists(con, table_name: str) -> bool:
    try:
        return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone() is not None
    except Exception:
        return False


def make_audit_row(
    *,
    source_name: str,
    source_type: str,
    primary_or_secondary: str,
    expected_path_or_url: str = "",
    available: bool = False,
    records_count: int | float = 0,
    latest_date: str | None = None,
    tickers_count: int | float = 0,
    coverage_scope: str = "",
    status: str = "UNKNOWN",
    message: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source_name": source_name,
        "source_type": source_type,
        "primary_or_secondary": primary_or_secondary,
        "expected_path_or_url": expected_path_or_url,
        "available": bool(available),
        "records_count": int(records_count or 0),
        "latest_date": latest_date or "",
        "tickers_count": int(tickers_count or 0),
        "coverage_scope": coverage_scope,
        "last_checked_at": now_iso(),
        "status": status,
        "message": message,
        "metadata_json": to_json(metadata),
    }


def empty_audit_df() -> pd.DataFrame:
    return pd.DataFrame(columns=AUDIT_RESULT_COLUMNS)


def build_source_inventory(config: dict | None = None) -> pd.DataFrame:
    """Executa auditorias leves e retorna o inventario consolidado.

    A funcao nao faz verificacoes online por padrao. RI e fontes externas sao
    auditadas apenas pela configuracao local, mantendo a rotina segura.
    """
    from src.data_quality.b3_audit import audit_b3_cotahist
    from src.data_quality.cvm_audit import audit_cvm_ipe
    from src.data_quality.news_event_audit import audit_event_pipeline, audit_news_hunter
    from src.data_quality.options_data_audit import audit_options_data
    from src.data_quality.profit_rtd_audit import audit_profit_excel
    from src.data_quality.ri_audit import audit_ri_sites, load_ri_urls
    from src.data_quality.valuation_audit import audit_valuation_outputs
    from src.utils import load_config

    cfg = config or load_config()
    db_path = project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    rows = [
        audit_profit_excel(),
        audit_b3_cotahist(
            cfg.get("b3", {}).get("raw_dir", "data/raw"),
            cfg.get("b3", {}).get("processed_dir", "data/processed"),
            db_path,
        ),
        audit_cvm_ipe(),
        audit_news_hunter(),
        audit_event_pipeline(db_path),
        audit_valuation_outputs(),
        audit_options_data(db_path),
    ]
    ri_rows = audit_ri_sites(load_ri_urls(), check_online=False)
    if isinstance(ri_rows, pd.DataFrame) and not ri_rows.empty:
        configured = int(ri_rows["url_configured"].fillna(False).astype(bool).sum())
        rows.append(
            make_audit_row(
                source_name="ri_sites",
                source_type="COMPANY_IR",
                primary_or_secondary="PRIMARY",
                expected_path_or_url="empresas.yaml",
                available=configured > 0,
                records_count=len(ri_rows),
                tickers_count=configured,
                coverage_scope="company_ir_urls",
                status="OK" if configured else "MISSING",
                message=f"{configured} URLs de RI configuradas.",
                metadata={"ri_sites": ri_rows.to_dict(orient="records")},
            )
        )
    else:
        rows.append(
            make_audit_row(
                source_name="ri_sites",
                source_type="COMPANY_IR",
                primary_or_secondary="PRIMARY",
                expected_path_or_url="empresas.yaml",
                status="MISSING",
                message="Nenhuma URL de RI encontrada nas configuracoes locais.",
            )
        )
    return pd.DataFrame(rows, columns=AUDIT_RESULT_COLUMNS)


def build_traceability_records(audit_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df is None or audit_df.empty:
        return pd.DataFrame(columns=TRACEABILITY_COLUMNS)
    rows: list[dict[str, Any]] = []
    created_at = now_iso()
    for _, row in audit_df.iterrows():
        metadata = {}
        try:
            metadata = json.loads(row.get("metadata_json") or "{}")
        except Exception:
            metadata = {}
        tickers = metadata.get("tickers") or metadata.get("underlyings") or []
        if not tickers:
            tickers = [""]
        if isinstance(tickers, str):
            tickers = [tickers]
        for ticker in tickers[:200]:
            rows.append(
                {
                    "created_at": created_at,
                    "ticker": str(ticker).upper() if ticker else "",
                    "data_domain": row.get("source_type", ""),
                    "source_name": row.get("source_name", ""),
                    "source_type": row.get("primary_or_secondary", ""),
                    "source_url_or_path": row.get("expected_path_or_url", ""),
                    "source_date": row.get("latest_date", ""),
                    "collected_at": row.get("last_checked_at", created_at),
                    "record_count": row.get("records_count", 0),
                    "checksum": "",
                    "metadata_json": row.get("metadata_json", "{}"),
                }
            )
    return pd.DataFrame(rows, columns=TRACEABILITY_COLUMNS)

