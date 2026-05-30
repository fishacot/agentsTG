"""Tests for orchestrator — greetings go through LLM/graph, not static HTML."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_orchestrator_greeting_uses_graph_not_static_template():
    from src.agents_tg.agents.orchestrator import orchestrator

    with patch.object(
        orchestrator,
        "app",
        new_callable=AsyncMock,
    ) as mock_app:
        mock_app.ainvoke.return_value = {
            "messages": [],
            "direct_reply": "Привет! Я <b>Егор</b>, координирую команду.",
            "plan": [],
            "current_step": 0,
        }
        reply = await orchestrator.process("привет", user_id="test")
        mock_app.ainvoke.assert_called_once()
        assert "Егор" in reply
