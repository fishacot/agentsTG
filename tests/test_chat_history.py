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


@pytest.mark.asyncio
async def test_task_scoped_history_isolated(store: ChatHistoryStore) -> None:
    await store.append("u1", "orchestrator", "user", "Task A", task_id="t-a")
    await store.append("u1", "orchestrator", "assistant", "Reply A", task_id="t-a")
    await store.append("u1", "orchestrator", "user", "Task B", task_id="t-b")
    turns_a = await store.get_recent("u1", "orchestrator", task_id="t-a")
    turns_b = await store.get_recent("u1", "orchestrator", task_id="t-b")
    assert len(turns_a) == 2
    assert turns_a[0].content == "Task A"
    assert len(turns_b) == 1
    assert turns_b[0].content == "Task B"


def test_format_for_prompt(store: ChatHistoryStore) -> None:
    turns = [
        ChatTurn(role="user", content="Question"),
        ChatTurn(role="assistant", content="Answer"),
    ]
    text = store.format_for_prompt(turns)
    assert "Пользователь: Question" in text
    assert "Ассистент: Answer" in text
