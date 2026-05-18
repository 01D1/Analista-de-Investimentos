"""Auditoria de configuracao e acesso leve aos sites de RI."""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
import yaml

from src.data_quality.source_inventory import resolve_path


RI_COLUMNS = ["ticker", "company_name", "ri_url"]


def _find_url(data: dict) -> str:
    for key, value in data.items():
        k = str(key).lower()
        if "ri" in k and "url" in k and value:
            return str(value)
        if k in {"ri", "site_ri", "website_ri", "url_ri", "ri_url"} and value:
            return str(value)
    return ""


def load_ri_urls(config_path: str | Path | None = None, empresas_yaml: str | Path | None = None) -> pd.DataFrame:
    candidates: list[Path] = []
    if empresas_yaml:
        p = resolve_path(empresas_yaml)
        if p:
            candidates.append(p)
    if config_path:
        p = resolve_path(config_path)
        if p:
            candidates.append(p)
    default = resolve_path("../12_PYTHON/pipeline banco completo/config/empresas.yaml")
    if default:
        candidates.append(default)
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        rows = []
        if isinstance(payload, dict) and isinstance(payload.get("empresas"), dict):
            payload = payload["empresas"]
        items = payload.items() if isinstance(payload, dict) else enumerate(payload if isinstance(payload, list) else [])
        for key, value in items:
            if not isinstance(value, dict):
                continue
            ticker = str(value.get("ticker") or key).upper()
            if not any(ch.isdigit() for ch in ticker):
                continue
            name = str(value.get("nome") or value.get("name") or value.get("company_name") or "")
            rows.append({"ticker": ticker, "company_name": name, "ri_url": _find_url(value)})
        if rows:
            return pd.DataFrame(rows, columns=RI_COLUMNS)
    return pd.DataFrame(columns=RI_COLUMNS)


def audit_ri_sites(ri_df: pd.DataFrame, check_online: bool = False, timeout: int = 10) -> pd.DataFrame:
    columns = ["ticker", "company_name", "ri_url", "url_configured", "checked_online", "status_code", "response_time_ms", "status", "message"]
    if ri_df is None or ri_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for _, row in ri_df.iterrows():
        url = str(row.get("ri_url") or "").strip()
        configured = bool(url)
        status_code = None
        elapsed = None
        status = "OK" if configured else "MISSING_URL"
        message = "URL de RI configurada." if configured else "URL de RI ausente."
        if configured and check_online:
            start = time.perf_counter()
            try:
                req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 data-audit"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status_code = int(resp.status)
                elapsed = int((time.perf_counter() - start) * 1000)
                status = "OK" if status_code < 400 else "WARNING"
                message = f"HTTP {status_code}"
            except urllib.error.HTTPError as exc:
                elapsed = int((time.perf_counter() - start) * 1000)
                status_code = int(exc.code)
                status = "WARNING" if status_code < 500 else "ERROR"
                message = f"HTTP {status_code}"
            except TimeoutError:
                elapsed = int((time.perf_counter() - start) * 1000)
                status = "TIMEOUT"
                message = "Timeout no acesso leve ao RI."
            except Exception as exc:
                elapsed = int((time.perf_counter() - start) * 1000)
                status = "ERROR"
                message = str(exc)
        elif not check_online and configured:
            status = "NOT_CHECKED"
            message = "URL configurada; verificacao online desabilitada."
        rows.append(
            {
                "ticker": row.get("ticker", ""),
                "company_name": row.get("company_name", ""),
                "ri_url": url,
                "url_configured": configured,
                "checked_online": bool(check_online),
                "status_code": status_code,
                "response_time_ms": elapsed,
                "status": status,
                "message": message,
            }
        )
    return pd.DataFrame(rows, columns=columns)
