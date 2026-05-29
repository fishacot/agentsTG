"""Tests for memory service fallback."""

import pytest

from src.agents_tg.services.memory_service import MemoryService


@pytest.fixture
def memory() -> MemoryService:
    svc = MemoryService()
    svc.memory = None
    return svc


@pytest.mark.asyncio
async def test_fallback_add_and_search(memory: MemoryService) -> None:
    await memory.add("Меня зовут Алекс", user_id="u1")
    await memory.add("Люблю Python", user_id="u1")

    results = await memory.search("Python", user_id="u1")
    assert any("Python" in r.get("text", "") for r in results)


@pytest.mark.asyncio
async def test_fallback_search_without_query_returns_recent(
    memory: MemoryService,
) -> None:
    await memory.add("Факт один", user_id="u2")
    await memory.add("Факт два", user_id="u2")

    results = await memory.search("", user_id="u2", limit=2)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_empty_add_ignored(memory: MemoryService) -> None:
    await memory.add("   ", user_id="u3")
    assert memory._facts_store.get("u3", []) == []
