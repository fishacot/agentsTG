"""Tests for tiered prompt builder."""

from src.agents_tg.services.prompt_builder import (
    PromptTier,
    detect_prompt_tier,
    is_capabilities_question,
    tools_for_tier,
)
from src.agents_tg.services.agent_runner import AgentTool, tool_result


def test_detect_light_tier_greeting():
    assert detect_prompt_tier("привет") == PromptTier.LIGHT
    assert detect_prompt_tier("как дела?") == PromptTier.LIGHT


def test_detect_full_tier_action():
    assert detect_prompt_tier("запиши заметку про встречу") == PromptTier.FULL
    assert detect_prompt_tier("найди лучший фреймворк") == PromptTier.FULL


def test_capabilities_question():
    assert is_capabilities_question("расскажи что ты можешь")
    assert not is_capabilities_question("запиши заметку")


async def _dummy(**kwargs):
    return tool_result(ok=True)


def test_light_tier_no_tools():
    tools = [
        AgentTool(name="x", description="d", parameters={}, handler=_dummy),
    ]
    assert tools_for_tier(tools, PromptTier.LIGHT) == []
