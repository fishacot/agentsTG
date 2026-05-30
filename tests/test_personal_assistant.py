"""Tests for personal assistant tools (no LLM)."""

import pytest

from src.agents_tg.agents.personal_assistant import PersonalAssistant


@pytest.fixture
def pa(tmp_path, monkeypatch) -> PersonalAssistant:
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))
    return PersonalAssistant()


@pytest.mark.asyncio
async def test_add_and_list_tasks(pa: PersonalAssistant) -> None:
    data = await pa.add_task("Купить молоко", due_date="завтра")
    assert data["ok"] is True
    assert data["title"] == "Купить молоко"
    listing = await pa.list_tasks()
    assert listing["tasks"][0]["title"] == "Купить молоко"


@pytest.mark.asyncio
async def test_create_note(pa: PersonalAssistant) -> None:
    result = await pa.create_obsidian_note("Идея", "Текст заметки")
    assert result["ok"] is True
    assert result["title"] == "Идея"
    assert result["path"].endswith("Идея.md")


@pytest.mark.asyncio
async def test_invalid_note_title_rejected(pa: PersonalAssistant) -> None:
    result = await pa.create_obsidian_note("[Title]", "x")
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_capabilities_faq_no_llm(pa: PersonalAssistant, monkeypatch) -> None:
    from unittest.mock import AsyncMock, patch

    with patch(
        "src.agents_tg.agents.personal_assistant.agent_runner.run",
        new_callable=AsyncMock,
    ) as mock_run:
        reply = await pa.process("расскажи что ты можешь", user_id="u1")
        mock_run.assert_not_called()
        assert "<b>Я Эльза</b>" in reply


@pytest.mark.asyncio
async def test_memory_faq_no_llm(pa: PersonalAssistant, monkeypatch) -> None:
    from unittest.mock import AsyncMock, patch

    with patch(
        "src.agents_tg.agents.personal_assistant.agent_runner.run",
        new_callable=AsyncMock,
    ) as mock_run:
        reply = await pa.process("ты можешь запоминать?", user_id="u1")
        mock_run.assert_not_called()
        assert "могу запоминать" in reply.lower()
