"""Tests for orchestrator — greetings go through LLM, not static HTML."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_orchestrator_greeting_uses_llm_not_static_template():
    from src.agents_tg.agents.orchestrator import orchestrator
    from src.agents_tg.services.agent_runner import agent_runner

    with patch.object(
        agent_runner,
        "run",
        new_callable=AsyncMock,
        return_value="Привет! Я <b>Егор</b>, координирую команду.",
    ) as mock_run:
        reply = await orchestrator.process("привет", user_id="test")
        mock_run.assert_called_once()
        assert "Егор" in reply


@pytest.mark.asyncio
async def test_orchestrator_task_uses_graph():
    from src.agents_tg.agents.orchestrator import orchestrator

    with patch.object(
        orchestrator,
        "app",
        new_callable=AsyncMock,
    ) as mock_app:
        mock_app.ainvoke.return_value = {
            "messages": [],
            "direct_reply": "",
            "plan": ["шаг 1"],
            "current_step": 1,
            "next_agent": "coder",
        }
        with patch.object(
            orchestrator,
            "coder_node",
            new_callable=AsyncMock,
            return_value={"messages": []},
        ):
            await orchestrator.process(
                "напиши функцию сортировки на python", user_id="test"
            )
        mock_app.ainvoke.assert_called_once()
