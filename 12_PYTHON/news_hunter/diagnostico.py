# -*- coding: utf-8 -*-
"""Diagnostico operacional do banco do News Hunter."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import config


def parse_news_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(raw)
            except (TypeError, ValueError, IndexError):
                return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _latest_by(rows: list[sqlite3.Row], field: str) -> dict[str, Any]:
    latest_row: sqlite3.Row | None = None
    latest_dt: datetime | None = None
    for row in rows:
        dt = parse_news_datetime(row[field])
        if dt is None:
            continue
        if latest_dt is None or dt > latest_dt:
            latest_dt = dt
            latest_row = row
    payload = _row_dict(latest_row)
    payload["parsed_at"] = _iso(latest_dt)
    return payload


def diagnosticar_banco(db_path: str | Path | None = None, limit: int = 10) -> dict[str, Any]:
    path = Path(db_path or config.ARQUIVO_BANCO)
    if not path.exists():
        return {
            "db_path": str(path),
            "exists": False,
            "total": 0,
            "error": "banco.db nao encontrado",
        }

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT id, titulo, link, fonte, categoria, data_pub, data_coleta, score,
                      resumo_curto, motivo_score
               FROM noticias"""
        ).fetchall()
        errors = conn.execute(
            "SELECT fonte, erro, data FROM erros_fonte ORDER BY data DESC LIMIT ?",
            (limit,),
        ).fetchall()
        last_rows = conn.execute(
            """SELECT id, titulo, link, fonte, categoria, data_pub, data_coleta, score
               FROM noticias
               ORDER BY data_coleta DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    by_source: dict[str, int] = {}
    for row in rows:
        fonte = str(row["fonte"] or "N/D")
        by_source[fonte] = by_source.get(fonte, 0) + 1

    return {
        "db_path": str(path),
        "exists": True,
        "total": len(rows),
        "latest_by_data_pub": _latest_by(rows, "data_pub"),
        "latest_by_data_coleta": _latest_by(rows, "data_coleta"),
        "top_sources": sorted(by_source.items(), key=lambda item: (-item[1], item[0]))[:limit],
        "recent_errors": [_row_dict(row) for row in errors],
        "latest_rows": [_row_dict(row) for row in last_rows],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostico do News Hunter")
    parser.add_argument("--db", default=config.ARQUIVO_BANCO, help="Caminho do banco SQLite")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(diagnosticar_banco(args.db, limit=args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
