"""Tests for LLM/plan budget helpers."""

from src.agents_tg.config.settings import AppSettings
from src.agents_tg.services.llm_budget import cap_plan_steps, max_tokens_for_tier
from src.agents_tg.services.prompts.tier_rules import PromptTier


def test_cap_plan_steps_trims(monkeypatch):
    monkeypatch.setenv("MAX_PLAN_STEPS", "3")
    monkeypatch.setenv("PLAN_MAX_STEPS", "3")
    steps = ["a", "b", "c", "d", "e"]
    trimmed, was = cap_plan_steps(steps)
    assert was is True
    assert len(trimmed) == 3
    assert trimmed == ["a", "b", "c"]


def test_max_tokens_full_tier(monkeypatch):
    monkeypatch.setenv("MAX_TOKENS_FULL_TIER", "800")
    cap = max_tokens_for_tier(PromptTier.FULL, profile_cap=1200, requested=1000)
    assert cap == 800


def test_settings_guardrail_defaults():
    s = AppSettings()
    assert s.PLAN_MAX_STEPS == 4
    assert s.PREFER_FILE_MEMORY is True
