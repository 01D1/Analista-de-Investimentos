"""
test_scheduler_intelligence.py
-------------------------------
Phase 4 — Scheduler integration tests for job_intelligence() (D-19).

Covers:
  - job_intelligence registered in _JOB_REGISTRY under key "intelligence"
  - job_intelligence() calls run_all() and returns formatted string
  - D-15 summary log emitted with required fields
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


def test_job_intelligence_registered():
    """D-19: job_intelligence is registered in _JOB_REGISTRY under key 'intelligence'."""
    from src.scheduler import _JOB_REGISTRY

    assert "intelligence" in _JOB_REGISTRY, (
        f"'intelligence' not found in _JOB_REGISTRY. Keys: {list(_JOB_REGISTRY.keys())}"
    )


@pytest.mark.xfail(reason="job_intelligence() not yet implemented — Plan 04-04")
def test_job_intelligence_calls_run_all(monkeypatch):
    """D-19: job_intelligence() calls run_all() and returns 'intelligence: ok=...' string."""
    from src.intelligence_layer import ThesisResult

    call_count = []

    def mock_run_all():
        call_count.append(1)
        return []

    mock_log = MagicMock()
    mock_log.info = lambda msg, **kw: None

    @contextmanager
    def mock_bind(prefix):
        yield f"{prefix}-test-run"

    monkeypatch.setattr("src.intelligence_layer.run_all", mock_run_all)
    monkeypatch.setattr("src.utils.logger.get_logger", lambda *a, **k: mock_log)
    monkeypatch.setattr("src.utils.logger.bind_run_id", mock_bind)

    from src.scheduler import job_intelligence

    result = job_intelligence()
    assert "intelligence" in result
    assert len(call_count) == 1


@pytest.mark.xfail(reason="job_intelligence() not yet implemented — Plan 04-04")
def test_job_intelligence_summary_log(monkeypatch):
    """D-15 + D-19: job_intelligence() emits structured summary log with source='intelligence'."""
    logged = []
    mock_log = MagicMock()
    mock_log.info = lambda msg, **kw: logged.append({"msg": str(msg), "kw": kw})

    @contextmanager
    def mock_bind(prefix):
        yield f"{prefix}-test-run"

    monkeypatch.setattr("src.utils.logger.get_logger", lambda *a, **k: mock_log)
    monkeypatch.setattr("src.utils.logger.bind_run_id", mock_bind)
    monkeypatch.setattr("src.intelligence_layer.run_all", lambda: [])

    from src.scheduler import job_intelligence

    job_intelligence()

    summary_logs = [r for r in logged if "summary" in r["msg"]]
    assert len(summary_logs) >= 1
    s = summary_logs[-1]
    assert s["kw"].get("source") == "intelligence"
    assert "duration_ms" in s["kw"]
    assert "records_inserted" in s["kw"]
