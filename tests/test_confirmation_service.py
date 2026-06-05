"""Tests for confirmation gates."""

from src.agents_tg.config.settings import AppSettings
from src.agents_tg.services.confirmation_service import confirmation_service


def test_requires_confirmation_when_disabled(monkeypatch):
    monkeypatch.setenv("REQUIRE_CONFIRM", "false")
    settings = AppSettings()
    assert settings.REQUIRE_CONFIRM is False
    assert (
        confirmation_service.requires_confirmation("update_project_status:done")
        is False
    )


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


def test_confirmation_ttl_expires(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from src.agents_tg.services.confirmation_service import (
        PendingConfirmation,
        confirmation_service,
    )

    monkeypatch.setenv("CONFIRMATION_TTL_SEC", "1")
    entry = confirmation_service.register(
        telegram_user_id=1,
        action="run_code",
        payload={},
    )
    confirmation_service._pending[entry.token] = PendingConfirmation(
        token=entry.token,
        telegram_user_id=1,
        action="run_code",
        payload={},
        created_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    assert confirmation_service.get(entry.token) is None


def test_run_code_in_gated_actions():
    from src.agents_tg.services.confirmation_service import GATED_ACTIONS

    assert "run_code" in GATED_ACTIONS
