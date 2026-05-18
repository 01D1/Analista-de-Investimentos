"""
test_scheduler_delivery.py
---------------------------
Phase 5 - Scheduler delivery tests covering DEL-04.

Covers:
  - job_morning_brief registrado em _JOB_REGISTRY com chave 'morning_brief'
  - Entrada morning_brief existe em schedules.yaml com cron correto
  - job_morning_brief() chama send_daily_brief() e retorna 'morning_brief: sent'
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


def test_morning_brief_registered():
    """DEL-04: job_morning_brief esta registrado em _JOB_REGISTRY."""
    from src.scheduler import _JOB_REGISTRY

    assert "morning_brief" in _JOB_REGISTRY, (
        f"'morning_brief' nao encontrado em _JOB_REGISTRY. Chaves: {list(_JOB_REGISTRY.keys())}"
    )


def test_morning_brief_cron_in_yaml():
    """DEL-04: entrada morning_brief existe em schedules.yaml."""
    import yaml
    from pathlib import Path

    path = Path(__file__).parent.parent / "config" / "schedules.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = [e["job"] for e in data.get("schedules", [])]
    assert "morning_brief" in jobs, (
        f"'morning_brief' nao encontrado em schedules.yaml. Encontrados: {jobs}"
    )


def test_morning_brief_calls_send_daily_brief(monkeypatch):
    """DEL-04: job_morning_brief() chama get_bot().send_daily_brief() e retorna 'morning_brief: sent'."""
    import sqlite3

    called = []
    mock_bot = MagicMock()
    mock_bot.send_daily_brief = lambda *a, **k: called.append(1) or True

    @contextmanager
    def mock_bind(prefix):
        yield f"{prefix}-test"

    monkeypatch.setattr("src.delivery.telegram_bot.get_bot", lambda: mock_bot)
    monkeypatch.setattr("src.utils.logger.bind_run_id", mock_bind)

    # Patch get_connection para retornar DB em memoria
    mock_conn = sqlite3.connect(":memory:")
    mock_conn.row_factory = sqlite3.Row
    mock_conn.executescript("""
        CREATE TABLE macro_series (
            id TEXT, series_code INT, series_name TEXT,
            date TEXT, value REAL, ingested_at TEXT
        );
        CREATE TABLE financial_dcf (
            id TEXT, ticker TEXT, computed_date TEXT,
            fair_value_brl REAL, upside_pct REAL
        );
        CREATE TABLE opportunity_signals (
            id TEXT, ticker TEXT, signal_type TEXT,
            description TEXT, conviction_score INT,
            computed_date TEXT
        );
    """)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: mock_conn)

    from src.scheduler import job_morning_brief

    result = job_morning_brief()
    assert "morning_brief" in result, f"Resultado esperado conter 'morning_brief', obteve: {result}"
    assert len(called) == 1, "send_daily_brief() deveria ser chamado exatamente 1 vez"
