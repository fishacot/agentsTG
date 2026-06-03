"""Tests for personal assistant tools (no LLM)."""

import pytest

from src.agents_tg.agents.personal_assistant import PersonalAssistant


@pytest.fixture
def pa(tmp_path, monkeypatch) -> PersonalAssistant:
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))
    return PersonalAssistant()


@pytest.mark.asyncio
async def test_add_and_list_tasks(pa: PersonalAssistant) -> None:
    uid = 12345
    data = await pa.add_task("Купить молоко", due_date="завтра", telegram_user_id=uid)
    assert data["ok"] is True
    assert data["title"] == "Купить молоко"
    listing = await pa.list_tasks(telegram_user_id=uid)
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
async def test_meta_questions_use_llm(pa: PersonalAssistant) -> None:
    from unittest.mock import AsyncMock, patch

    with patch(
        "src.agents_tg.agents.personal_assistant.agent_runner.run",
        new_callable=AsyncMock,
        return_value="Живой ответ от LLM",
    ) as mock_run:
        for msg in (
            "расскажи что ты можешь",
            "ты можешь запоминать?",
            "кто ты",
            "отправь сводку новостей об ии",
        ):
            reply = await pa.process(msg, user_id="u1")
            assert reply == "Живой ответ от LLM"
        assert mock_run.call_count == 4
