"""Tests for reminder service (in-memory mode)."""

from datetime import datetime, timedelta

import pytest

from src.agents_tg.services.reminder_service import (
    MORNING_DIGEST_MARKER,
    MORNING_DIGEST_TEXT,
    ReminderService,
)
from src.agents_tg.utils.timezone_utils import get_app_tz


@pytest.mark.asyncio
async def test_schedule_in_memory():
    svc = ReminderService()
    tz = get_app_tz()
    fire_local = datetime.now(tz) + timedelta(minutes=5)
    result = await svc.schedule(
        telegram_user_id=123,
        chat_id=456,
        text="выпить воды",
        fire_at_local=fire_local,
    )
    assert result["ok"] is True
    pending = await svc.list_pending(123)
    assert len(pending) == 1
    assert "выпить воды" in pending[0]["text"]


@pytest.mark.asyncio
async def test_morning_digest_reschedule_marker():
    svc = ReminderService()
    delivered: list[str] = []

    async def send_fn(chat_id, user_id, body, agent_key):
        delivered.append(body)

    svc.set_send_fn(send_fn)
    tz = get_app_tz()
    fire = datetime.now(tz) - timedelta(minutes=1)
    await svc.schedule(
        telegram_user_id=1,
        chat_id=2,
        text=MORNING_DIGEST_TEXT,
        fire_at_local=fire,
        is_digest=True,
    )
    await svc._fire_due()
    assert delivered
    assert MORNING_DIGEST_TEXT in delivered[0]
    pending = await svc.list_pending(1)
    assert any(MORNING_DIGEST_MARKER in p["text"] for p in pending)
