"""Tests for environment context builder."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents_tg.services.environment_context import (
    AgentEnvironment,
    build_environment,
)


@pytest.fixture
def fake_message() -> MagicMock:
    msg = MagicMock()
    msg.chat.type = "private"
    msg.chat.id = 12345
    msg.from_user.id = 999
    msg.from_user.username = "testuser"
    return msg


@pytest.mark.asyncio
async def test_build_environment_dm(monkeypatch, fake_message) -> None:
    monkeypatch.setattr(
        "src.agents_tg.services.environment_context.memory_service.get_all",
        AsyncMock(return_value=[{"text": "likes coffee"}]),
    )
    env = await build_environment(
        message=fake_message,
        agent_key="personal_assistant",
        coordinator=None,
        tool_names=["create_obsidian_note"],
        dm_recent="Пользователь: hi\nАссистент: hello",
    )
    assert isinstance(env, AgentEnvironment)
    assert env.is_group is False
    assert env.user_id == "999"
    assert env.memory_facts_count == 1
    block = env.to_prompt_block()
    assert "личные сообщения" in block
    assert "create_obsidian_note" in block


@pytest.mark.asyncio
async def test_build_environment_group(monkeypatch, fake_message) -> None:
    fake_message.chat.type = "supergroup"
    coordinator = MagicMock()
    coordinator.get_recent_context.return_value = "[12:00] @user: hello"

    monkeypatch.setattr(
        "src.agents_tg.services.environment_context.memory_service.get_all",
        AsyncMock(return_value=[]),
    )
    env = await build_environment(
        message=fake_message,
        agent_key="research",
        coordinator=coordinator,
        tool_names=["deep_research"],
    )
    assert env.is_group is True
    block = env.to_prompt_block()
    assert "групповой чат" in block
    coordinator.get_recent_context.assert_called_once()
