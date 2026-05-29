"""Tests for chat history store."""

import pytest

from src.agents_tg.services.chat_history import ChatHistoryStore, ChatTurn


@pytest.fixture
def store() -> ChatHistoryStore:
    return ChatHistoryStore()


@pytest.mark.asyncio
async def test_append_and_get_recent(store: ChatHistoryStore) -> None:
    await store.append("u1", "research", "user", "Hello")
    await store.append("u1", "research", "assistant", "Hi there")
    turns = await store.get_recent("u1", "research")
    assert len(turns) == 2
    assert turns[0].role == "user"
    assert turns[1].content == "Hi there"


def test_format_for_prompt(store: ChatHistoryStore) -> None:
    turns = [
        ChatTurn(role="user", content="Question"),
        ChatTurn(role="assistant", content="Answer"),
    ]
    text = store.format_for_prompt(turns)
    assert "Пользователь: Question" in text
    assert "Ассистент: Answer" in text
