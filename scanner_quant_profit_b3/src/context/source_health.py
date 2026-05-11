"""Health checks das fontes locais usadas pela camada de eventos."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


HEALTH_COLUMNS = [
    "source_name",
    "status",
    "available",
    "records_count",
    "latest_date",
    "age_days",
    "coverage_hint",
    "path",
    "message",
    "checked_at",
    "metadata_json",
]

DEFAULT_CONFIG = {
    "sources": {
        "csv": {"enabled": True, "path": "data/events/market_events_example.csv"},
        "news_hunter": {"enabled": True, "db_path": "../12_PYTHON/news_hunter/banco.db"},
        "macro_calendar": {"enabled": True, "path": "../12_PYTHON/news_hunter/dados/calendario_economico.json"},
        "cvm": {"enabled": True, "base_dir": "../12_PYTHON/pipeline banco completo/data/qualitative/processed"},
        "releases": {"enabled": True, "base_dir": "../12_PYTHON/pipeline banco completo/data/qualitative/events"},
    },
    "health": {
        "max_stale_days": 45,
        "warning_stale_days": 15,
        "min_csv_records": 1,
        "min_news_records": 1,
        "min_macro_records": 1,
        "min_cvm_files": 1,
        "min_release_records": 1,
    },
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else _project_root() / "config" / "events.yaml"
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if not path.exists():
        return config
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return config
    for section, value in loaded.items():
        if isinstance(value, dict) and isinstance(config.get(section), dict):
            config[section].update(value)
        else:
            config[section] = value
    return config


def _resolve(path_value: str | Path | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else (_project_root() / path).resolve()


def _age_days(date_value: Any) -> float | None:
    date = pd.to_datetime(date_value, errors="coerce", utc=True)
    if pd.isna(date):
        return None
    date = date.tz_convert(None)
    return float((pd.Timestamp.now().normalize() - date.normalize()).days)


def _date_str(value: Any) -> str | None:
    date = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(date):
        return None
    date = date.tz_convert(None)
    return date.strftime("%Y-%m-%d")


def _status(records: int, latest_date: Any, *, min_records: int, max_stale_days: int, warning_stale_days: int) -> tuple[str, str]:
    if records <= 0:
        return "EMPTY", "Fonte existe, mas não possui registros."
    age = _age_days(latest_date)
    if age is None:
        return "WARNING", "Fonte possui registros, mas a data mais recente não foi identificada."
    if age < -7:
        return "WARNING", f"Fonte possui data futura inconsistente ({latest_date})."
    if age > max_stale_days:
        return "STALE", f"Último registro há {age:.0f} dias."
    if age > warning_stale_days or records < min_records:
        return "WARNING", f"Fonte disponível, mas com baixa quantidade ou última atualização há {age:.0f} dias."
    return "OK", "Fonte disponível e dentro dos limites de saúde."


def _row(source_name: str, status: str, available: bool, records_count: int, latest_date: Any, path: Path | None, message: str, metadata: dict | None = None) -> dict[str, Any]:
    age = _age_days(latest_date)
    return {
        "source_name": source_name,
        "status": status,
        "available": bool(available),
        "records_count": int(records_count or 0),
        "latest_date": _date_str(latest_date),
        "age_days": age,
        "coverage_hint": "usable" if status == "OK" else "verificar_fonte",
        "path": str(path) if path else "",
        "message": message,
        "checked_at": _now(),
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }


def _source_config(config: dict[str, Any], name: str) -> dict[str, Any]:
    return (config.get("sources") or {}).get(name) or {}


def check_csv_health(config: dict[str, Any]) -> dict[str, Any]:
    health = config.get("health") or {}
    path = _resolve(_source_config(config, "csv").get("path"))
    if path is None or not path.exists():
        return _row("csv", "MISSING", False, 0, None, path, "Arquivo CSV de eventos não encontrado.")
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return _row("csv", "ERROR", True, 0, None, path, f"Erro ao ler CSV: {exc}")
    latest = df["event_date"].max() if "event_date" in df.columns and not df.empty else None
    status, message = _status(
        len(df),
        latest,
        min_records=int(health.get("min_csv_records", 1)),
        max_stale_days=int(health.get("max_stale_days", 45)),
        warning_stale_days=int(health.get("warning_stale_days", 15)),
    )
    return _row("csv", status, True, len(df), latest, path, message, {"columns": list(df.columns)})


def check_news_hunter_health(config: dict[str, Any]) -> dict[str, Any]:
    health = config.get("health") or {}
    path = _resolve(_source_config(config, "news_hunter").get("db_path"))
    if path is None or not path.exists():
        return _row("news_hunter", "MISSING", False, 0, None, path, "Banco do News Hunter não encontrado.")
    try:
        with sqlite3.connect(path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='noticias'").fetchone()
            if not exists:
                return _row("news_hunter", "ERROR", True, 0, None, path, "Tabela noticias ausente.")
            count = int(con.execute("SELECT COUNT(*) FROM noticias").fetchone()[0])
            cols = {row[1] for row in con.execute("PRAGMA table_info(noticias)").fetchall()}
            date_col = "data_pub" if "data_pub" in cols else "data_coleta" if "data_coleta" in cols else None
            latest = con.execute(f"SELECT MAX({date_col}) FROM noticias").fetchone()[0] if date_col else None
    except Exception as exc:
        return _row("news_hunter", "ERROR", True, 0, None, path, f"Erro ao consultar News Hunter: {exc}")
    status, message = _status(
        count,
        latest,
        min_records=int(health.get("min_news_records", 1)),
        max_stale_days=int(health.get("max_stale_days", 45)),
        warning_stale_days=int(health.get("warning_stale_days", 15)),
    )
    return _row("news_hunter", status, True, count, latest, path, message)


def _read_json_list(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("events") or data.get("eventos") or data.get("data") or data.get("items") or []
    return data if isinstance(data, list) else []


def check_macro_calendar_health(config: dict[str, Any]) -> dict[str, Any]:
    health = config.get("health") or {}
    path = _resolve(_source_config(config, "macro_calendar").get("path"))
    if path is None or not path.exists():
        return _row("macro_calendar", "MISSING", False, 0, None, path, "Calendário econômico não encontrado.")
    try:
        data = _read_json_list(path)
    except Exception as exc:
        return _row("macro_calendar", "ERROR", True, 0, None, path, f"Erro ao ler calendário macro: {exc}")
    latest = max((_date_str(item.get("data") or item.get("event_date") or item.get("date")) for item in data if isinstance(item, dict)), default=None)
    status, message = _status(
        len(data),
        latest,
        min_records=int(health.get("min_macro_records", 1)),
        max_stale_days=int(health.get("max_stale_days", 45)),
        warning_stale_days=int(health.get("warning_stale_days", 15)),
    )
    return _row("macro_calendar", status, True, len(data), latest, path, message)


def check_cvm_health(config: dict[str, Any]) -> dict[str, Any]:
    health = config.get("health") or {}
    root = _resolve(_source_config(config, "cvm").get("base_dir"))
    if root is None or not root.exists():
        return _row("cvm", "MISSING", False, 0, None, root, "Diretório CVM/IPE processado não encontrado.")
    paths = list(root.glob("*/cvm_*index.json"))
    latest_dates = []
    tickers = set()
    for path in paths:
        tickers.add(path.parent.name.upper())
        try:
            data = _read_json_list(path)
        except Exception:
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            latest_dates.append(_date_str(item.get("Data_Referencia") or item.get("Data_Entrega") or item.get("date")))
    latest = max([date for date in latest_dates if date], default=None)
    status, message = _status(
        len(paths),
        latest,
        min_records=int(health.get("min_cvm_files", 1)),
        max_stale_days=int(health.get("max_stale_days", 45)),
        warning_stale_days=int(health.get("warning_stale_days", 15)),
    )
    return _row("cvm", status, True, len(paths), latest, root, message, {"tickers": sorted(tickers), "tickers_count": len(tickers)})


def check_releases_health(config: dict[str, Any]) -> dict[str, Any]:
    health = config.get("health") or {}
    root = _resolve(_source_config(config, "releases").get("base_dir"))
    if root is not None and root.name.lower() != "events":
        root = root / "events"
    if root is None or not root.exists():
        return _row("releases", "MISSING", False, 0, None, root, "Diretório de releases/eventos não encontrado.")
    paths = list(root.glob("*/events.json"))
    count = 0
    latest_dates = []
    tickers = set()
    for path in paths:
        tickers.add(path.parent.name.upper())
        try:
            data = _read_json_list(path)
        except Exception:
            continue
        count += len(data)
        for item in data:
            if isinstance(item, dict):
                latest_dates.append(_date_str(item.get("date") or item.get("event_date")))
    latest = max([date for date in latest_dates if date], default=None)
    status, message = _status(
        count,
        latest,
        min_records=int(health.get("min_release_records", 1)),
        max_stale_days=int(health.get("max_stale_days", 45)),
        warning_stale_days=int(health.get("warning_stale_days", 15)),
    )
    return _row("releases", status, True, count, latest, root, message, {"files": len(paths), "tickers": sorted(tickers), "tickers_count": len(tickers)})


def check_all_sources(config_path: str | Path = "config/events.yaml") -> pd.DataFrame:
    config = _load_config(config_path)
    rows = [
        check_csv_health(config),
        check_news_hunter_health(config),
        check_macro_calendar_health(config),
        check_cvm_health(config),
        check_releases_health(config),
    ]
    return pd.DataFrame(rows, columns=HEALTH_COLUMNS)
