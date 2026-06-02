"""Outer loop replan suffix handling."""

import pytest

from src.agents_tg.services.agent_outer_loop import AgentOuterLoop


@pytest.mark.asyncio
async def test_outer_loop_replan_suffix_continues_for_orchestrator(monkeypatch):
    loop = AgentOuterLoop()
    calls: list[str] = []

    async def fake_dispatch(*, agent_key, user_text, user_id, environment):
        calls.append(user_text)
        if len(calls) == 1:
            return "частичный результат [[REPLAN]]"
        return "финал"

    monkeypatch.setattr(loop, "_dispatch_once", fake_dispatch)

    out = await loop.run(
        agent_key="orchestrator",
        user_text="сделай план",
        user_id="1",
    )
    assert out == "финал"
    assert len(calls) == 2
    assert "[[REPLAN]]" in calls[1]
