"""Tests for config/settings.py — model_post_init startup validation.

NOTE: Settings uses env_ignore_empty=True which means empty string env vars
are ignored and the .env file values take precedence. Tests that check for
missing-key validation must use a tmp_path that has NO .env file, so the
Settings instance finds empty strings only from env vars that are absent.

Strategy: each test creates an isolated Settings subclass that points to
tmp_path for its env_file, ensuring no real .env is loaded.
"""
import sys
import pytest
from pathlib import Path
from pydantic_settings import SettingsConfigDict


def _make_isolated_settings(tmp_path, env_content: str = ""):
    """Create a Settings subclass pointing to a temp .env with given content."""
    # Write the temp .env (even if empty)
    env_file = tmp_path / ".env"
    env_file.write_text(env_content, encoding="utf-8")

    # Re-import to get fresh class (avoid cached singleton)
    sys.modules.pop("config.settings", None)
    sys.modules.pop("config", None)

    from config.settings import Settings, REQUIRED_IN_PRODUCTION

    class IsolatedSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=[str(env_file)],
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
            env_ignore_empty=True,
        )

    return IsolatedSettings, REQUIRED_IN_PRODUCTION


def test_startup_guard_development_mode(tmp_path, monkeypatch):
    """Development mode: missing keys do NOT trigger sys.exit."""
    monkeypatch.setenv("ENV", "development")
    IsolatedSettings, _ = _make_isolated_settings(tmp_path, "")
    s = IsolatedSettings()
    assert s.env == "development"


def test_startup_guard_production_missing_keys(tmp_path, monkeypatch):
    """Production mode + missing required key: sys.exit(1) called."""
    monkeypatch.setenv("ENV", "production")
    # Create a .env with no credential keys — only ENV set
    IsolatedSettings, _ = _make_isolated_settings(tmp_path, "ENV=production\n")
    # Ensure credential keys are absent from env
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        IsolatedSettings()
    assert exc_info.value.code == 1


def test_startup_guard_production_all_keys_set(tmp_path, monkeypatch):
    """Production mode + all required keys: no exit."""
    env_content = (
        "ENV=production\n"
        "ANTHROPIC_API_KEY=sk-ant-test\n"
        "TELEGRAM_BOT_TOKEN=123:abc\n"
        "TELEGRAM_CHAT_ID=-100\n"
    )
    IsolatedSettings, _ = _make_isolated_settings(tmp_path, env_content)
    s = IsolatedSettings()
    assert s.env == "production"
