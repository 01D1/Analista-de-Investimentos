"""
test_scheduler_ingestion.py
Tests for ingestion scheduler wiring — ING-07.
Verifies job registration, init_db calls, D-15 summary logs,
subprocess list form, and schedules.yaml entries.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml


# ─── Test 1: Registry ────────────────────────────────────────────────────────

def test_all_four_jobs_registered():
    """All 4 new ingestion jobs must be in _JOB_REGISTRY."""
    from src.scheduler import _JOB_REGISTRY
    required = {"cvm_ingest", "bcb_macro", "b3_prices", "news_ingest"}
    missing = required - set(_JOB_REGISTRY.keys())
    assert not missing, f"Missing from _JOB_REGISTRY: {missing}"


# ─── Test 2: init_db called before ingest ────────────────────────────────────

def test_job_bcb_macro_calls_init_db_before_ingest(monkeypatch):
    """job_bcb_macro() must call init_db() before ingest_all_series()."""
    call_order = []

    def mock_init_db(*args, **kwargs):
        call_order.append("init_db")

    mock_result = {
        "inserted": 5, "updated": 0, "failed": [], "stale": [],
        "last_ingested_at": "2026-05-10T12:00:00",
    }

    def mock_ingest_all(conn):
        call_order.append("ingest_all_series")
        return mock_result

    monkeypatch.setattr("src.ingestion.db.init_db", mock_init_db)
    monkeypatch.setattr("src.ingestion.bcb.ingest_all_series", mock_ingest_all)

    # Also patch get_connection to return a mock
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: mock_conn)

    from src.scheduler import job_bcb_macro
    job_bcb_macro()

    assert call_order.index("init_db") < call_order.index("ingest_all_series")


# ─── Test 3: D-15 summary log ────────────────────────────────────────────────

def test_job_bcb_macro_emits_summary_log(monkeypatch, capsys):
    """job_bcb_macro() emits INFO log with source='bcb_macro' after completion."""
    logged_records = []

    mock_result = {
        "inserted": 10, "updated": 0, "failed": [], "stale": [],
        "last_ingested_at": "2026-05-10T12:00:00",
    }
    monkeypatch.setattr("src.ingestion.db.init_db", lambda *a, **k: None)
    monkeypatch.setattr("src.ingestion.bcb.ingest_all_series", lambda conn: mock_result)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: MagicMock())

    from src.scheduler import job_bcb_macro
    import src.scheduler as sched_mod

    with patch.object(sched_mod, "log") as mock_log:
        def capture_log_info(msg, **kwargs):
            logged_records.append({"msg": str(msg), "kwargs": kwargs})
        mock_log.info = capture_log_info
        mock_log.warning = MagicMock()

        job_bcb_macro()

    # Find the summary log
    summary_logs = [r for r in logged_records if "summary" in r["msg"]]
    assert len(summary_logs) >= 1
    summary = summary_logs[-1]
    assert summary["kwargs"].get("source") == "bcb_macro"
    assert "records_inserted" in summary["kwargs"]
    assert "duration_ms" in summary["kwargs"]
    assert "status" in summary["kwargs"]
    assert "last_ingested_at" in summary["kwargs"]


# ─── Test 4: Subprocess list form ────────────────────────────────────────────

def test_job_news_ingest_uses_subprocess_list_form(monkeypatch):
    """job_news_ingest() must call subprocess.run with a list, not a string."""
    captured_calls = []

    def mock_subprocess_run(args, **kwargs):
        captured_calls.append(args)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        return mock_result

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("src.ingestion.db.init_db", lambda *a, **k: None)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: MagicMock())
    monkeypatch.setattr(
        "src.ingestion.news_sync.sync_news_to_ingestion_db",
        lambda *a, **k: 0,
    )

    from src.scheduler import job_news_ingest
    job_news_ingest()

    assert len(captured_calls) == 1
    args = captured_calls[0]
    assert isinstance(args, list), f"Expected list, got {type(args)}: {args}"
    assert "main.py" in args


# ─── Test 5: news sync called after subprocess ───────────────────────────────

def test_job_news_ingest_calls_sync_after_subprocess(monkeypatch):
    """sync_news_to_ingestion_db() must be called after subprocess.run completes."""
    call_order = []

    def mock_subprocess_run(args, **kwargs):
        call_order.append("subprocess.run")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        return mock_result

    def mock_sync(*args, **kwargs):
        call_order.append("sync_news_to_ingestion_db")
        return 5

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setattr("src.ingestion.db.init_db", lambda *a, **k: None)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: MagicMock())
    monkeypatch.setattr(
        "src.ingestion.news_sync.sync_news_to_ingestion_db", mock_sync
    )

    from src.scheduler import job_news_ingest
    job_news_ingest()

    assert call_order.index("subprocess.run") < call_order.index("sync_news_to_ingestion_db")


# ─── Test 6: b3_prices iterates active tickers ───────────────────────────────

def test_job_b3_prices_iterates_active_tickers(monkeypatch):
    """job_b3_prices() calls fetch_and_store() once per active ticker."""
    called_tickers = []
    mock_settings = MagicMock()
    mock_settings.active_tickers = ["PETR4", "VALE3", "BBAS3"]

    def mock_fetch_and_store(ticker, conn, start_date=None):
        called_tickers.append(ticker)
        return {"inserted": 1, "gaps": 0, "ticker": ticker}

    monkeypatch.setattr("src.ingestion.db.init_db", lambda *a, **k: None)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: MagicMock())

    with patch("config.settings.settings", mock_settings):
        mock_scraper = MagicMock()
        mock_scraper.fetch_and_store.side_effect = mock_fetch_and_store
        with patch("src.ingestion.b3_scraper.B3Scraper", return_value=mock_scraper):
            from src.scheduler import job_b3_prices
            job_b3_prices()

    assert set(called_tickers) == {"PETR4", "VALE3", "BBAS3"}


# ─── Test 7: schedules.yaml entries ──────────────────────────────────────────

def test_schedules_yaml_has_ingestion_entries():
    """schedules.yaml must contain entries for all 4 ingestion jobs."""
    schedules_path = Path(__file__).parent.parent / "config" / "schedules.yaml"
    assert schedules_path.exists(), f"schedules.yaml not found at {schedules_path}"

    with open(schedules_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Handle both top-level list and nested structure
    if isinstance(data, list):
        jobs = {entry["job"] for entry in data if "job" in entry}
    elif isinstance(data, dict):
        # Try common keys like "jobs" or "schedules"
        entries = data.get("jobs") or data.get("schedules") or []
        jobs = {entry["job"] for entry in entries if "job" in entry}
    else:
        jobs = set()

    required = {"cvm_ingest", "bcb_macro", "b3_prices", "news_ingest"}
    missing = required - jobs
    assert not missing, f"Missing from schedules.yaml: {missing}"
