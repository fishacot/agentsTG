"""Tests for agent runtime."""

from types import SimpleNamespace

import pytest

from src.agents_tg.services.agent_runtime import (
    AgentRunResult,
    OutboundSink,
    agent_runtime,
)


def test_run_result_extras():
    r = AgentRunResult(messages=["first", "second", "third"])
    assert r.primary == "first"
    assert r.extras == ["second", "third"]


@pytest.mark.asyncio
async def test_outbound_sink():
    sink = OutboundSink()
    await sink.push("hello")
    await sink.push("NO_REPLY")
    assert sink.drain_messages() == ["hello"]


@pytest.mark.asyncio
async def test_run_inbound_passes_is_group_to_process_fn():
    """Regression: del is_group before process_fn caused UnboundLocalError."""

    seen: dict[str, bool] = {}

    async def process_fn(*, message, user_text, is_group, coordinator):
        seen["is_group"] = is_group
        return f"echo:{user_text}"

    msg = SimpleNamespace(from_user=SimpleNamespace(id=1))
    result = await agent_runtime.run_inbound(
        agent_key="personal_assistant",
        process_fn=process_fn,
        message=msg,
        user_text="hi",
        is_group=False,
        coordinator=None,
    )
    assert seen["is_group"] is False
    assert result.primary == "echo:hi"


@pytest.mark.asyncio
async def test_outbound_sink_with_coalesce():
    sink = OutboundSink(coalesce_idle_ms=400)
    await sink.push("a")
    await sink.push("b")
    assert sink.drain_messages() == ["a\nb"]
