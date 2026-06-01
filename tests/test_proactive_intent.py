"""Tests for proactive intent materialization."""

import pytest

from src.agents_tg.services.proactive_intent import (
    _extract_daily_time,
    try_schedule_from_message,
)
from src.agents_tg.services.reminder_service import ReminderService


def test_extract_daily_time_11_msk():
    assert _extract_daily_time(
        "каждый день в 11 утра по мск присылай доброе утро"
    ) == (11, 0)


def test_extract_daily_time_reversed_phrase():
    assert _extract_daily_time("в 11:00 каждый день") == (11, 0)


@pytest.mark.asyncio
async def test_try_schedule_daily_autonomy_question(monkeypatch):
    svc = ReminderService()
    monkeypatch.setattr(
        "src.agents_tg.services.reminder_service.reminder_service",
        svc,
    )

    msg = (
        "Какой у тебь часовой пояс и сможешь ли ты автономно мне писать "
        "с напоминаниями, например каждый день в 11 утра "
        "по мск присылать мне сообщение доброе утро"
    )
    lines = await try_schedule_from_message(
        msg,
        telegram_user_id=42,
        chat_id=99,
        agent_key="personal_assistant",
    )
    assert lines
    pending = await svc.list_pending(42)
    assert len(pending) == 1
    assert "Доброе утро" in pending[0]["text"]
