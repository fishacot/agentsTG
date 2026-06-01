"""Tests for daily reminder recurrence."""

from datetime import datetime, timedelta

import pytest

from src.agents_tg.services.reminder_service import ReminderService
from src.agents_tg.utils.timezone_utils import get_app_tz


@pytest.mark.asyncio
async def test_cron_deliver_fn_used_when_set():
    svc = ReminderService()
    cron_calls: list[tuple] = []

    async def cron_fn(chat_id, user_id, text, agent_key):
        cron_calls.append((chat_id, user_id, text, agent_key))

    svc.set_cron_deliver_fn(cron_fn)
    await svc._deliver(8, 7, "water", "personal_assistant")
    assert cron_calls == [(8, 7, "water", "personal_assistant")]


@pytest.mark.asyncio
async def test_daily_recurrence_reschedules_in_memory():
    svc = ReminderService()
    delivered: list[str] = []

    async def send_fn(chat_id, user_id, body, agent_key):
        delivered.append(body)

    svc.set_send_fn(send_fn)
    tz = get_app_tz()
    fire = datetime.now(tz) - timedelta(minutes=1)
    await svc.schedule(
        telegram_user_id=7,
        chat_id=8,
        text="ping",
        fire_at_local=fire,
        recurrence="daily",
    )
    await svc._fire_due()
    assert delivered
    pending = await svc.list_pending(7)
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"
