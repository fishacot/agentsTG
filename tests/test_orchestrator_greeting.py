"""Tests for orchestrator zero-LLM greeting path."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents_tg.services.capability_templates import build_egor_greeting_html
from src.agents_tg.services.prompt_builder import is_pure_greeting


def test_pure_greeting_detected():
    assert is_pure_greeting("привет")
    assert is_pure_greeting("Привет!")
    assert not is_pure_greeting("запиши заметку")


def test_egor_greeting_html():
    html = build_egor_greeting_html()
    assert "<b>Егор</b>" in html
    assert "@" in html


@pytest.mark.asyncio
async def test_orchestrator_greeting_no_llm():
    from src.agents_tg.agents.orchestrator import orchestrator

    with patch(
        "src.agents_tg.agents.orchestrator.llm_client.chat",
        new_callable=AsyncMock,
    ) as mock_chat:
        reply = await orchestrator.process("привет", user_id="test")
        mock_chat.assert_not_called()
        assert "Егор" in reply
