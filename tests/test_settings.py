"""Tests for application settings configuration."""

import pytest

from src.agents_tg.config.settings import AppSettings


class TestAppSettings:
    """Test suite for AppSettings."""

    def test_defaults(self):
        """Verify default values are set correctly."""
        settings = AppSettings()
        # assert settings.BOT_TOKEN == ""  # Skip if .env is present
        assert "groq.com" in settings.GROQ_API_BASE
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DEBUG is False

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch):
        """Verify environment variables override defaults."""
        monkeypatch.setenv("BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        settings = AppSettings()
        assert settings.BOT_TOKEN == "test_token_123"
        assert settings.LOG_LEVEL == "DEBUG"

    def test_root_dir(self):
        """Verify ROOT_DIR points to project root."""
        settings = AppSettings()
        assert settings.ROOT_DIR.exists()
        assert (settings.ROOT_DIR / "pyproject.toml").exists()

    def test_llm_provider_chain_default(self):
        settings = AppSettings()
        assert settings.llm_provider_chain_list == ["gemini", "groq"]

    def test_llm_provider_chain_override(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_CHAIN", "groq,gemini")
        settings = AppSettings()
        assert settings.llm_provider_chain_list == ["groq", "gemini"]

    def test_gemini_defaults(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
        settings = AppSettings()
        assert "generativelanguage.googleapis.com" in settings.GEMINI_API_BASE
        assert settings.GEMINI_MODEL == "gemini-2.5-flash"
