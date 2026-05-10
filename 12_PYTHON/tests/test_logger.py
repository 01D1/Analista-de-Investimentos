"""Tests for src/utils/logger.py — configure_logging, bind_run_id, retention."""
import pytest
from pathlib import Path
from loguru import logger as _loguru_logger


def test_get_logger_returns_bound_logger(tmp_path):
    from src.utils.logger import configure_logging, get_logger
    configure_logging(tmp_path, level="DEBUG")
    log = get_logger("test.module")
    assert log is not None


def test_run_id_binding(tmp_path):
    from src.utils.logger import configure_logging, get_logger, bind_run_id
    configure_logging(tmp_path, level="DEBUG")
    log = get_logger("test.run_id")

    captured_extras = []

    def capture_sink(message):
        captured_extras.append(message.record["extra"])

    _loguru_logger.add(capture_sink, level="DEBUG")

    with bind_run_id("pytest") as run_id:
        log.info("inside context")
        assert run_id.startswith("pytest-")

    log.info("outside context")

    inside = captured_extras[-2]
    assert inside.get("run_id", "-") != "-"
    outside = captured_extras[-1]
    assert outside.get("run_id", "-") == "-"


def test_configure_logging_idempotent(tmp_path):
    """configure_logging() called twice does not add duplicate handlers."""
    from src.utils.logger import configure_logging
    configure_logging(tmp_path, level="INFO")
    configure_logging(tmp_path, level="INFO")
