"""Tests for VPS/Groq risk mitigations: notebook, budget."""

from __future__ import annotations

import pytest

from src.agents_tg.services.llm_budget import LLMBudget
from src.agents_tg.services.notebook import append_notebook, load_notebook_block


def test_notebook_append_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.agents_tg.services.notebook.notebook_path",
        lambda uid: tmp_path / "NOTEBOOK.md",
    )
    append_notebook(99, text="Тестовая заметка", agent_key="personal_assistant")
    block = load_notebook_block("99")
    assert "Тестовая заметка" in block


@pytest.mark.asyncio
async def test_llm_budget_exhausted(monkeypatch):
    from src.agents_tg.config import settings as settings_mod

    class _S(settings_mod.AppSettings):
        LLM_SOFT_DAILY_CALLS: int = 2

    monkeypatch.setattr(settings_mod, "get_settings", lambda: _S())
    budget = LLMBudget()
    await budget.record("u1")
    await budget.record("u1")
    assert await budget.is_exhausted("u1")


@pytest.mark.asyncio
async def test_should_force_light_at_85_percent(monkeypatch):
    from src.agents_tg.config import settings as settings_mod

    class _S(settings_mod.AppSettings):
        LLM_SOFT_DAILY_CALLS: int = 10
        GROQ_DEFER_HEAVY_ON_BUDGET: bool = True

    monkeypatch.setattr(settings_mod, "get_settings", lambda: _S())
    budget = LLMBudget()
    for _ in range(9):
        await budget.record("u2")
    assert await budget.should_force_light_tier("u2")
