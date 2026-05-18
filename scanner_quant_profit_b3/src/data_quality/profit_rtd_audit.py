"""Auditoria leve do arquivo Excel alimentado pelo Profit RTD."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.source_inventory import make_audit_row, resolve_path
from src.utils import load_config


ASSET_COLUMNS = ["ticker", "ativo", "asset", "symbol", "papel"]
PRICE_COLUMNS = ["last", "ultimo", "último", "preco", "preço", "close", "cotacao", "cotação"]
CRITICAL_ALIASES = {
    "last": PRICE_COLUMNS,
    "open": ["open", "abertura"],
    "high": ["high", "max", "máximo", "maximo"],
    "low": ["low", "min", "mínimo", "minimo"],
    "volume": ["volume", "vol"],
    "trades": ["trades", "negocios", "negócios"],
}


def _norm(col: str) -> str:
    return str(col).strip().lower()


def _find_column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {_norm(c): c for c in columns}
    for alias in aliases:
        if _norm(alias) in normalized:
            return normalized[_norm(alias)]
    for col in columns:
        n = _norm(col)
        if any(_norm(alias) in n for alias in aliases):
            return col
    return None


def audit_profit_excel(config_path: str | Path = "config.yaml") -> dict:
    try:
        cfg = load_config() if str(config_path) == "config.yaml" else {}
        if str(config_path) != "config.yaml":
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        excel_path = resolve_path(cfg.get("profit_excel_path", "data/realtime/RTD PROFIT.xlsx"))
        sheet_name = cfg.get("profit_sheet_name", "Planilha1")
        if not excel_path or not excel_path.exists():
            return {
                **make_audit_row(
                    source_name="profit_rtd",
                    source_type="REALTIME",
                    primary_or_secondary="PRIMARY",
                    expected_path_or_url=str(excel_path or ""),
                    status="MISSING",
                    message="Arquivo Excel do Profit RTD nao encontrado.",
                ),
                "file_exists": False,
                "sheet_exists": False,
                "rows_count": 0,
                "assets_count": 0,
                "critical_fields_ok": False,
                "missing_columns": list(CRITICAL_ALIASES),
                "stale_warning": False,
            }
        xls = pd.ExcelFile(excel_path)
        sheet_exists = sheet_name in xls.sheet_names
        if not sheet_exists:
            return {
                **make_audit_row(
                    source_name="profit_rtd",
                    source_type="REALTIME",
                    primary_or_secondary="PRIMARY",
                    expected_path_or_url=str(excel_path),
                    available=True,
                    status="ERROR",
                    message=f"Aba {sheet_name} nao encontrada no Excel.",
                    metadata={"sheets": xls.sheet_names},
                ),
                "file_exists": True,
                "sheet_exists": False,
                "rows_count": 0,
                "assets_count": 0,
                "critical_fields_ok": False,
                "missing_columns": list(CRITICAL_ALIASES),
                "stale_warning": False,
            }
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        columns = list(df.columns)
        asset_col = _find_column(columns, ASSET_COLUMNS)
        missing = [key for key, aliases in CRITICAL_ALIASES.items() if _find_column(columns, aliases) is None]
        assets_count = int(df[asset_col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique()) if asset_col else 0
        mtime = datetime.fromtimestamp(excel_path.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        stale = age_hours > 24
        numeric_ok = True
        price_col = _find_column(columns, PRICE_COLUMNS)
        if price_col:
            numeric_ok = pd.to_numeric(df[price_col], errors="coerce").notna().any()
        critical_ok = not missing and assets_count > 0 and numeric_ok
        status = "OK" if critical_ok and not stale else "WARNING"
        if stale:
            status = "STALE"
        return {
            **make_audit_row(
                source_name="profit_rtd",
                source_type="REALTIME",
                primary_or_secondary="PRIMARY",
                expected_path_or_url=str(excel_path),
                available=True,
                records_count=len(df),
                latest_date=mtime.date().isoformat(),
                tickers_count=assets_count,
                coverage_scope="realtime_quotes",
                status=status,
                message="Profit RTD auditado com sucesso." if critical_ok else "Excel existe, mas ha campos criticos ausentes ou vazios.",
                metadata={"sheet": sheet_name, "missing_columns": missing, "age_hours": age_hours},
            ),
            "file_exists": True,
            "sheet_exists": True,
            "rows_count": int(len(df)),
            "assets_count": assets_count,
            "critical_fields_ok": bool(critical_ok),
            "missing_columns": missing,
            "stale_warning": bool(stale),
        }
    except Exception as exc:
        return {
            **make_audit_row(
                source_name="profit_rtd",
                source_type="REALTIME",
                primary_or_secondary="PRIMARY",
                status="ERROR",
                message=f"Erro ao auditar Profit RTD: {exc}",
            ),
            "file_exists": False,
            "sheet_exists": False,
            "rows_count": 0,
            "assets_count": 0,
            "critical_fields_ok": False,
            "missing_columns": list(CRITICAL_ALIASES),
            "stale_warning": False,
        }

