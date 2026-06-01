"""Tests for confirmation gates."""

import pytest

from src.agents_tg.config.settings import AppSettings
from src.agents_tg.services.confirmation_service import confirmation_service


def test_requires_confirmation_when_disabled(monkeypatch):
    monkeypatch.setenv("REQUIRE_CONFIRM", "false")
    settings = AppSettings()
    assert settings.REQUIRE_CONFIRM is False
    assert confirmation_service.requires_confirmation("update_project_status:done") is False


def test_requires_confirmation_when_enabled(monkeypatch):
    monkeypatch.setenv("REQUIRE_CONFIRM", "true")
    settings = AppSettings()
    assert settings.REQUIRE_CONFIRM is True

    def _requires(action: str) -> bool:
        if not AppSettings().REQUIRE_CONFIRM:
            return False
        from src.agents_tg.services.confirmation_service import GATED_ACTIONS

        return action in GATED_ACTIONS

    assert _requires("update_project_status:done") is True


def test_register_and_consume():
    entry = confirmation_service.register(
        telegram_user_id=42,
        action="update_project_status:done",
        payload={"status": "done"},
    )
    assert confirmation_service.get(entry.token) is not None
    consumed = confirmation_service.consume(entry.token)
    assert consumed is not None
    assert confirmation_service.get(entry.token) is None
