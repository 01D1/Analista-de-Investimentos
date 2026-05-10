"""Tests for src/utils/retry.py — exponential backoff + jitter + IngestionError."""
import time
import pytest
from unittest.mock import patch


def test_success_on_first_attempt():
    """Decorated function succeeds first try — no sleeps."""
    from src.utils.retry import retry
    call_count = 0

    @retry(attempts=3, delay=0.01, jitter=0.0)
    def flaky():
        nonlocal call_count
        call_count += 1
        return "ok"

    assert flaky() == "ok"
    assert call_count == 1


def test_backoff_jitter(monkeypatch):
    """Failed attempts sleep with exponential backoff + jitter."""
    from src.utils.retry import retry
    from src.utils.errors import IngestionError
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    @retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("boom")

    with pytest.raises(IngestionError):
        always_fails()

    assert len(sleeps) == 2
    assert sleeps[0] >= 2.0
    assert sleeps[1] >= 4.0


def test_ingestion_error_raised_on_exhaustion():
    """Final attempt raises IngestionError (not bare exception)."""
    from src.utils.retry import retry
    from src.utils.errors import IngestionError

    @retry(attempts=2, delay=0.0, jitter=0.0, exceptions=(RuntimeError,))
    def always_fails():
        raise RuntimeError("api down")

    with pytest.raises(IngestionError) as exc_info:
        always_fails()

    err = exc_info.value
    assert "always_fails" in str(err)
    assert err.cause == "api down"


def test_non_matching_exception_propagates():
    """Exception NOT in exceptions tuple propagates immediately (no retry)."""
    from src.utils.retry import retry

    @retry(attempts=3, delay=0.0, jitter=0.0, exceptions=(ValueError,))
    def raises_type_error():
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        raises_type_error()
