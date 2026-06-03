"""Tests for prompt tier detection (services.prompts.tier_rules)."""

from src.agents_tg.services.prompts import (
    PromptTier,
    build_system_prompt,
    detect_prompt_tier,
    load_soul,
    tools_for_tier,
)
from src.agents_tg.services.tools.builtin import AgentTool, tool_result


async def _dummy(**kwargs):
    return tool_result(ok=True)


def test_detect_light_tier_greeting():
    assert detect_prompt_tier("привет") == PromptTier.LIGHT
    assert detect_prompt_tier("как дела?") == PromptTier.LIGHT
    assert detect_prompt_tier("кто ты") == PromptTier.LIGHT
    assert detect_prompt_tier("") == PromptTier.LIGHT


def test_detect_light_tier_news_digest():
    assert detect_prompt_tier("отправь сводку новостей об ии") == PromptTier.LIGHT
    assert detect_prompt_tier("расскажи что ты можешь") == PromptTier.LIGHT
    assert detect_prompt_tier("объясни что такое REST") == PromptTier.LIGHT


def test_detect_standard_tier_ambiguous():
    assert detect_prompt_tier("хочу обсудить планы на неделю") == PromptTier.STANDARD


def test_detect_full_tier_action():
    assert detect_prompt_tier("запиши заметку про встречу") == PromptTier.FULL
    assert detect_prompt_tier("найди лучший фреймворк") == PromptTier.FULL
    assert detect_prompt_tier("покажи мои дела") == PromptTier.FULL
    assert detect_prompt_tier("напомни через час") == PromptTier.FULL
    assert detect_prompt_tier("каждый день в 11 доброе утро") == PromptTier.FULL


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


def test_standard_tier_schedule_reminder():
    tools = [
        AgentTool(
            name="remember_about_user", description="d", parameters={}, handler=_dummy
        ),
        AgentTool(
            name="schedule_reminder", description="d", parameters={}, handler=_dummy
        ),
    ]
    active = tools_for_tier(tools, PromptTier.STANDARD, "напомни завтра")
    assert {t.name for t in active} == {"remember_about_user", "schedule_reminder"}


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


def test_load_soul_personal_assistant():
    soul = load_soul("personal_assistant")
    assert isinstance(soul, str)
    assert len(soul) > 50


def test_light_prompt_shorter_than_full():
    soul = "\n".join(f"line {i}" for i in range(40))
    env = "Режим: dm\nVault Obsidian: /vault\n" + "\n".join(
        f"extra {i}" for i in range(20)
    )
    light = build_system_prompt(
        tier=PromptTier.LIGHT,
        human_name="Эльза",
        designation="ассистент",
        soul=soul,
        env_block=env,
        history_block="",
        memory_block="",
        output_hints="",
        include_web_tools=False,
        user_id="u1",
    )
    full = build_system_prompt(
        tier=PromptTier.FULL,
        human_name="Эльза",
        designation="ассистент",
        soul=soul,
        env_block=env,
        history_block="",
        memory_block="",
        output_hints="",
        include_web_tools=True,
        user_id="u1",
    )
    assert len(light) < len(full)
    assert "Протокол агента в Telegram" not in light
