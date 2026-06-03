"""Tests for tiered prompt builder."""

from src.agents_tg.services.agent_runner import AgentTool, tool_result
from src.agents_tg.services.prompt_builder import (
    PromptTier,
    detect_prompt_tier,
    tools_for_tier,
)


def test_detect_light_tier_greeting():
    assert detect_prompt_tier("привет") == PromptTier.LIGHT
    assert detect_prompt_tier("как дела?") == PromptTier.LIGHT
    assert detect_prompt_tier("кто ты") == PromptTier.LIGHT


def test_detect_light_tier_news_digest():
    assert detect_prompt_tier("отправь сводку новостей об ии") == PromptTier.LIGHT
    assert detect_prompt_tier("расскажи что ты можешь") == PromptTier.LIGHT


def test_detect_full_tier_action():
    assert detect_prompt_tier("запиши заметку про встречу") == PromptTier.FULL
    assert detect_prompt_tier("найди лучший фреймворк") == PromptTier.FULL
    assert detect_prompt_tier("покажи мои дела") == PromptTier.FULL


async def _dummy(**kwargs):
    return tool_result(ok=True)


def test_light_tier_no_tools():
    tools = [
        AgentTool(name="x", description="d", parameters={}, handler=_dummy),
        AgentTool(name="list_tasks", description="d", parameters={}, handler=_dummy),
    ]
    assert tools_for_tier(tools, PromptTier.LIGHT, "привет") == []


def test_standard_tier_remember_only_by_default():
    tools = [
        AgentTool(
            name="remember_about_user", description="d", parameters={}, handler=_dummy
        ),
        AgentTool(name="list_tasks", description="d", parameters={}, handler=_dummy),
        AgentTool(name="add_task", description="d", parameters={}, handler=_dummy),
    ]
    active = tools_for_tier(tools, PromptTier.STANDARD, "сводка новостей об ии")
    assert [t.name for t in active] == ["remember_about_user"]


def test_standard_tier_list_tasks_when_asked():
    tools = [
        AgentTool(
            name="remember_about_user", description="d", parameters={}, handler=_dummy
        ),
        AgentTool(name="list_tasks", description="d", parameters={}, handler=_dummy),
    ]
    active = tools_for_tier(tools, PromptTier.STANDARD, "покажи мои дела")
    assert {t.name for t in active} == {"remember_about_user", "list_tasks"}


def test_web_standard_tier_no_deep_research():
    tools = [
        AgentTool(
            name="remember_about_user", description="d", parameters={}, handler=_dummy
        ),
        AgentTool(name="deep_research", description="d", parameters={}, handler=_dummy),
    ]
    active = tools_for_tier(
        tools, PromptTier.STANDARD, "найди новости", include_web_tools=True
    )
    assert [t.name for t in active] == ["remember_about_user"]
