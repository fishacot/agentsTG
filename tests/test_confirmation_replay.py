"""Tests for confirmation replay handlers."""

import pytest

from src.agents_tg.services.confirmation_replay import (
    format_replay_message,
    replay_confirmed_action,
)
from src.agents_tg.services.confirmation_service import PendingConfirmation


@pytest.mark.asyncio
async def test_replay_run_code(monkeypatch):
    async def fake_run_code(code: str, *, timeout_sec: int = 30):
        return {"stdout": code, "exit_code": 0}

    monkeypatch.setattr(
        "src.agents_tg.sandbox.docker_runner.run_code",
        fake_run_code,
    )
    entry = PendingConfirmation(
        token="t1",
        telegram_user_id=1,
        action="run_code",
        payload={"code": "print(1)", "timeout_sec": 30},
    )
    result = await replay_confirmed_action(entry)
    assert result.get("ok") is True
    assert result.get("result", {}).get("stdout") == "print(1)"


@pytest.mark.asyncio
async def test_replay_update_project_status_done(monkeypatch):
    async def fake_update(uid, *, project_id=None, status=""):
        return {"ok": True, "status": status}

    monkeypatch.setattr(
        "src.agents_tg.services.shared_context.shared_context.update_project_status",
        fake_update,
    )
    monkeypatch.setattr(
        "src.agents_tg.services.workspace_memory.refresh_memory_md",
        lambda *a, **k: None,
    )
    entry = PendingConfirmation(
        token="t2",
        telegram_user_id=42,
        action="update_project_status:done",
        payload={"status": "done"},
    )
    result = await replay_confirmed_action(entry)
    assert result.get("ok") is True


def test_format_replay_message():
    assert "✅" in format_replay_message({"ok": True})
    assert "❌" in format_replay_message({"ok": False, "error": "x"})
