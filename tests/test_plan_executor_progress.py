"""Plan executor progress + verify integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents_tg.services.plan_executor import plan_executor


@pytest.mark.asyncio
async def test_execute_steps_calls_progress_and_deliver(monkeypatch):
    task = await plan_executor.create_task(
        telegram_user_id=1,
        title="t",
        steps=[("research", "шаг 1"), ("coder", "шаг 2")],
    )
    message = MagicMock()
    message.chat.id = 1
    message.from_user.id = 1
    message.message_id = 1

    progress_calls: list[tuple[int, int, str]] = []
    deliver_calls: list[str] = []

    async def progress_fn(cur, total, agent):
        progress_calls.append((cur, total, agent))

    async def deliver_fn(_msg, text):
        deliver_calls.append(text)

    async def fake_dispatch(*_a, **_k):
        return "готово"

    monkeypatch.setattr(
        "src.agents_tg.gateway.agent_dispatch.dispatch_agent",
        fake_dispatch,
    )

    final = await plan_executor.execute_steps(
        task,
        message=message,
        user_text="задача",
        process_fn=AsyncMock(),
        deliver_fn=deliver_fn,
        progress_fn=progress_fn,
    )
    assert final == "готово"
    assert len(progress_calls) == 2
    assert any("Шаг 1/2" in d for d in deliver_calls)
