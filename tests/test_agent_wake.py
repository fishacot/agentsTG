"""Tests for proactive agent wake."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.agents_tg.services.agent_runtime import AgentRunResult, TriggerKind, agent_runtime
from src.agents_tg.services.agent_wake import AgentWakeService


@pytest.mark.asyncio
async def test_run_scheduled_silent_on_heartbeat_ok():
    async def process_fn(**kwargs):
        return "HEARTBEAT_OK"

    result = await agent_runtime.run_scheduled(
        agent_key="personal_assistant",
        telegram_user_id=123,
        chat_id=456,
        user_text="[heartbeat]",
        trigger=TriggerKind.CRON,
        process_fn=process_fn,
    )
    assert result.silent is True
    assert result.primary is None


@pytest.mark.asyncio
async def test_run_scheduled_delivers_message():
    async def process_fn(**kwargs):
        return "Привет! Как продвигается проект?"

    result = await agent_runtime.run_scheduled(
        agent_key="personal_assistant",
        telegram_user_id=123,
        chat_id=456,
        user_text="[heartbeat]",
        trigger=TriggerKind.CRON,
        process_fn=process_fn,
    )
    assert result.silent is False
    assert "проект" in (result.primary or "")


@pytest.mark.asyncio
async def test_heartbeat_pass_skips_recent_users():
    wake = AgentWakeService()
    send = AsyncMock()
    wake.set_send_fn(send)
    wake.set_process_fn(AsyncMock(return_value="hello"))

    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=1)
    with patch(
        "src.agents_tg.services.agent_wake.user_contact_service.list_wake_candidates",
        new=AsyncMock(
            return_value=[
                {
                    "telegram_user_id": 1,
                    "chat_id": 10,
                    "agent_key": "personal_assistant",
                    "last_inbound_at": recent,
                    "last_outbound_at": None,
                    "last_heartbeat_at": None,
                }
            ]
        ),
    ):
        await wake.run_heartbeat_pass()

    send.assert_not_called()


@pytest.mark.asyncio
async def test_heartbeat_pass_wakes_quiet_user():
    wake = AgentWakeService()
    send = AsyncMock()
    process = AsyncMock(return_value="Добрый день! Есть открытые задачи.")
    wake.set_send_fn(send)
    wake.set_process_fn(process)

    now = datetime.now(timezone.utc)
    quiet = now - timedelta(hours=13)
    with patch(
        "src.agents_tg.services.agent_wake.user_contact_service.list_wake_candidates",
        new=AsyncMock(
            return_value=[
                {
                    "telegram_user_id": 1,
                    "chat_id": 10,
                    "agent_key": "personal_assistant",
                    "last_inbound_at": quiet,
                    "last_outbound_at": None,
                    "last_heartbeat_at": None,
                }
            ]
        ),
    ), patch(
        "src.agents_tg.services.agent_wake.agent_runtime.run_scheduled",
        new=AsyncMock(
            return_value=AgentRunResult(messages=["Добрый день! Есть открытые задачи."])
        ),
    ), patch(
        "src.agents_tg.services.agent_wake.user_contact_service.record_outbound",
        new=AsyncMock(),
    ), patch(
        "src.agents_tg.services.agent_wake.user_contact_service.record_heartbeat",
        new=AsyncMock(),
    ):
        await wake.run_heartbeat_pass()

    send.assert_called_once()


def test_load_heartbeat_default():
    from src.agents_tg.services.workspace_memory import load_heartbeat_md

    text = load_heartbeat_md(999999)
    assert "HEARTBEAT_OK" in text


@pytest.mark.asyncio
async def test_run_scheduled_reminder_llm_delivery():
    wake = AgentWakeService()
    send = AsyncMock()
    wake.set_send_fn(send)
    wake.set_process_fn(AsyncMock(return_value="Доброе утро! Напомню про встречу."))

    with patch(
        "src.agents_tg.services.agent_wake.get_settings"
    ) as mock_settings:
        mock_settings.return_value.REMINDER_LLM_DELIVERY = True
        await wake.run_scheduled_reminder(
            chat_id=10,
            telegram_user_id=1,
            text="встреча",
            agent_key="personal_assistant",
        )

    send.assert_called_once()
    assert "⏰" in send.call_args[0][2]


@pytest.mark.asyncio
async def test_run_event_wake_precomputed():
    wake = AgentWakeService()
    send = AsyncMock()
    wake.set_send_fn(send)

    with patch(
        "src.agents_tg.services.agent_wake.user_contact_service.record_outbound",
        new=AsyncMock(),
    ), patch(
        "src.agents_tg.services.memory_service.memory_service.add_journal_entry",
        new=AsyncMock(),
    ):
        await wake.run_event_wake(
            agent_key="research",
            telegram_user_id=1,
            chat_id=10,
            prompt="",
            precomputed="Итог исследования: Python 3.13",
        )

    send.assert_called_once()
    assert "Python" in send.call_args[0][2]

