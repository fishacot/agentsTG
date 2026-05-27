"""Tests for application settings configuration."""

import pytest

from src.agents_tg.config.settings import AppSettings


class TestAppSettings:
    """Test suite for AppSettings."""

    def test_defaults(self):
        """Verify default values are set correctly."""
        settings = AppSettings()
        # assert settings.BOT_TOKEN == ""  # Skip if .env is present
        assert "huggingface.co" in settings.QWEN_API_BASE or "router.huggingface" in settings.QWEN_API_BASE
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

    def test_src_dir(self):
        """Verify SRC_DIR property points to src/."""
        settings = AppSettings()
        assert settings.SRC_DIR == settings.ROOT_DIR / "src"
        assert settings.SRC_DIR.exists()
