"""Tests for agent runtime."""

from src.agents_tg.services.agent_runtime import AgentRunResult, OutboundSink


def test_run_result_extras():
    r = AgentRunResult(messages=["first", "second", "third"])
    assert r.primary == "first"
    assert r.extras == ["second", "third"]


def test_outbound_sink():
    sink = OutboundSink()
    sink.push("hello")
    sink.push("NO_REPLY")
    assert sink.messages == ["hello"]
