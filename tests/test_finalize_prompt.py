"""Tests for structured finalize directives."""

from src.agents_tg.services.prompts.finalize_directives import (
    FINALIZE_USER_REPLY,
    build_finalize_prompt,
)


def test_finalize_has_html_structure_markers():
    assert "<h2>" in FINALIZE_USER_REPLY
    assert "<h3>" in FINALIZE_USER_REPLY
    assert "Telegram HTML" in FINALIZE_USER_REPLY


def test_build_finalize_short_without_tools():
    prompt = build_finalize_prompt(has_tool_results=False)
    assert len(prompt) < len(FINALIZE_USER_REPLY)
    assert "инструмент" in prompt.lower() or "JSON" in prompt


def test_build_finalize_full_with_tools():
    prompt = build_finalize_prompt(has_tool_results=True)
    assert prompt == FINALIZE_USER_REPLY.strip()
