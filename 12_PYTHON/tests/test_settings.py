"""Tests for config/settings.py — model_post_init startup validation."""
import pytest


def test_startup_guard_development_mode(tmp_path, monkeypatch):
    """Development mode: missing keys do NOT trigger sys.exit."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import importlib, sys
    sys.modules.pop("config.settings", None)
    sys.modules.pop("config", None)
    from config.settings import Settings
    s = Settings()
    assert s.env == "development"


def test_startup_guard_production_missing_keys(monkeypatch):
    """Production mode + missing required key: sys.exit(1) called."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    import sys
    sys.modules.pop("config.settings", None)
    sys.modules.pop("config", None)
    with pytest.raises(SystemExit) as exc_info:
        from config.settings import Settings
        Settings()
    assert exc_info.value.code == 1


def test_startup_guard_production_all_keys_set(monkeypatch, tmp_path):
    """Production mode + all required keys: no exit."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100")
    import sys
    sys.modules.pop("config.settings", None)
    sys.modules.pop("config", None)
    from config.settings import Settings
    s = Settings()
    assert s.env == "production"
