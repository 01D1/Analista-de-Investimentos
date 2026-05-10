"""
Tests for FOUND-02: news_hunter/config.py has no hardcoded token fallbacks.
Token must default to empty string when env var is unset.
"""
import importlib.util
import sys
import pytest
from pathlib import Path


def _load_news_hunter_config(monkeypatch, token=None, chat_id=None):
    """Helper: load news_hunter/config.py in isolation."""
    if token is None:
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_TOKEN", token)
    if chat_id is None:
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_CHAT_ID", chat_id)

    spec = importlib.util.spec_from_file_location(
        "news_hunter_config",
        Path(__file__).parent.parent / "news_hunter" / "config.py",
    )
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg


def test_no_hardcoded_telegram_token(monkeypatch):
    """TELEGRAM_TOKEN defaults to empty string when env var not set."""
    cfg = _load_news_hunter_config(monkeypatch)
    assert cfg.TELEGRAM_TOKEN == "", (
        f"TELEGRAM_TOKEN should be empty string, got: {cfg.TELEGRAM_TOKEN!r}. "
        "Remove hardcoded fallback from news_hunter/config.py."
    )
    assert cfg.TELEGRAM_CHAT_ID == "", (
        f"TELEGRAM_CHAT_ID should be empty string, got: {cfg.TELEGRAM_CHAT_ID!r}. "
        "Remove hardcoded fallback from news_hunter/config.py."
    )


def test_token_loaded_from_env(monkeypatch):
    """TELEGRAM_TOKEN read from env when set."""
    cfg = _load_news_hunter_config(monkeypatch, token="test-token-123", chat_id="-999")
    assert cfg.TELEGRAM_TOKEN == "test-token-123"
    assert cfg.TELEGRAM_CHAT_ID == "-999"
