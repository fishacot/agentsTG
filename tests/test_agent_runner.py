"""Tests for agent_runner prompt assembly and tiers."""

from src.agents_tg.services.agent_runner import AgentTool, tool_result
from src.agents_tg.services.prompt_builder import (
    PromptTier,
    build_system_prompt,
    detect_prompt_tier,
    tools_for_tier,
)


async def _noop(**kwargs):
    return tool_result(ok=True)


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


def test_full_tier_detected_for_note_request():
    assert detect_prompt_tier("запиши заметку про встречу") == PromptTier.FULL


def test_light_tier_strips_tools():
    tools = [
        AgentTool(name="x", description="d", parameters={}, handler=_noop),
        AgentTool(name="remember_about_user", description="d", parameters={}, handler=_noop),
    ]
    assert tools_for_tier(tools, PromptTier.LIGHT) == []
    assert len(tools_for_tier(tools, PromptTier.FULL)) == 2
    standard = tools_for_tier(tools, PromptTier.STANDARD)
    assert len(standard) == 1
    assert standard[0].name == "remember_about_user"


def test_web_full_tier_research_only_with_explicit_search():
    tools = [
        AgentTool(name="remember_about_user", description="d", parameters={}, handler=_noop),
        AgentTool(name="deep_research", description="d", parameters={}, handler=_noop),
    ]
    no_search = tools_for_tier(
        tools, PromptTier.FULL, "напиши план MVP", include_web_tools=True
    )
    assert [t.name for t in no_search] == ["remember_about_user"]
    with_search = tools_for_tier(
        tools, PromptTier.FULL, "найди best practices", include_web_tools=True
    )
    assert {t.name for t in with_search} == {"remember_about_user", "deep_research"}


def test_parse_tool_arguments_null():
    from src.agents_tg.services.agent_runner import parse_tool_arguments

    assert parse_tool_arguments("null", "u42") == {"user_id": "u42"}
    assert parse_tool_arguments('{"fact":"dev"}', "u1") == {"fact": "dev", "user_id": "u1"}
