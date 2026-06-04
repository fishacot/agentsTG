"""Tests for message pipeline dedupe and followup queue."""

import asyncio

import pytest

from src.agents_tg.services.message_pipeline import MessagePipeline


@pytest.mark.asyncio
async def test_dedupe_in_memory():
    pipe = MessagePipeline()
    assert await pipe.is_duplicate("coder", 1, 100) is False
    assert await pipe.is_duplicate("coder", 1, 100) is True
    assert await pipe.is_duplicate("coder", 1, 101) is False


@pytest.mark.asyncio
async def test_pre_claim_before_gateway_dispatch_is_duplicate():
    """Regression: inbound handler must not call is_duplicate before gateway."""
    from src.agents_tg.gateway.envelope import OpenClawEnvelope
    from src.agents_tg.gateway.router import gateway_router
    from src.agents_tg.services.message_pipeline import message_pipeline

    await message_pipeline.is_duplicate("personal_assistant", 1, 200)
    env = OpenClawEnvelope(
        chat_id=1,
        user_id=7,
        text="привет",
        message_id=200,
        agent_key="personal_assistant",
    )
    result = await gateway_router.dispatch(env)
    assert result.duplicate is True


@pytest.mark.asyncio
async def test_followup_queue_while_busy():
    pipe = MessagePipeline()
    processed: list[str] = []

    class Msg:
        chat = type("C", (), {"id": 42})()
        from_user = type("U", (), {"id": 7})()
        message_id = 1
        text = "a"

    async def handler(msg, *, combined_text=None):
        processed.append(combined_text or msg.text)
        await asyncio.sleep(0.05)

    msg = Msg()
    pipe._busy["coder:42"] = True
    pipe.queue_followup(
        agent_key="coder", message=msg, handler=handler, combined_text="queued"
    )
    pipe._busy["coder:42"] = False
    await pipe.drain_followups("coder", 42)
    assert processed == ["queued"]


@pytest.mark.asyncio
async def test_debounce_flush_calls_handler_after_delay():
    """DM debounce must invoke handler (regression: double run_lock caused deadlock)."""
    pipe = MessagePipeline(debounce_ms=50)
    processed: list[str | None] = []

    class Msg:
        chat = type("C", (), {"id": 42})()
        from_user = type("U", (), {"id": 7})()
        message_id = 1
        text = "hi"

    async def handler(msg, *, combined_text=None):
        processed.append(combined_text or msg.text)

    msg = Msg()
    await pipe.enqueue_debounced(agent_key="coder", message=msg, handler=handler)
    await asyncio.sleep(0.15)
    assert processed == ["hi"]
