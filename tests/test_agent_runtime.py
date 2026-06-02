"""Tests for agent runtime."""

import pytest

from src.agents_tg.services.agent_runtime import AgentRunResult, OutboundSink


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
async def test_outbound_sink_with_coalesce():
    sink = OutboundSink(coalesce_idle_ms=400)
    await sink.push("a")
    await sink.push("b")
    assert sink.drain_messages() == ["a\nb"]
