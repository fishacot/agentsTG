"""Tests for deterministic tool policy hook."""

import pytest

from src.agents_tg.gateway.hooks.tool_policy import before_tool_policy_guard
from src.agents_tg.gateway.tool_policies import (
    is_tool_denied_for_agent_with_args,
    is_tool_allowed_for_tier,
)
from src.agents_tg.services.prompts.tier_rules import PromptTier
from src.agents_tg.services.tools.builtin import AgentTool, tool_result


async def _dummy(**kwargs):
    return tool_result(ok=True)


@pytest.mark.asyncio
async def test_agent_deny_run_code_for_pa():
    reason = is_tool_denied_for_agent_with_args(
        "personal_assistant", "run_code", {"user_id": "1"}
    )
    assert reason is not None
    assert "run_code" in reason


@pytest.mark.asyncio
async def test_tier_light_denies_all_tools():
    tools = [
        AgentTool(name="remember_about_user", description="d", parameters={}, handler=_dummy),
    ]
    assert not is_tool_allowed_for_tier(
        tool_name="remember_about_user",
        tier=PromptTier.LIGHT,
        user_message="привет",
        include_web_tools=False,
        registered_tools=tools,
    )


@pytest.mark.asyncio
async def test_hook_denies_tier_mismatch():
    tools = [
        AgentTool(name="deep_research", description="d", parameters={}, handler=_dummy),
    ]
    result = await before_tool_policy_guard(
        agent_key="research",
        user_id="42",
        tool_name="deep_research",
        args={"user_id": "42"},
        context={
            "tier": PromptTier.LIGHT,
            "user_message": "привет",
            "include_web_tools": True,
            "registered_tools": tools,
        },
    )
    assert result is not None
    assert result.get("deny") is True


@pytest.mark.asyncio
async def test_schedule_reminder_requires_text():
    reason = is_tool_denied_for_agent_with_args(
        "personal_assistant",
        "schedule_reminder",
        {"user_id": "1", "when": "tomorrow"},
    )
    assert reason is not None
    assert "text" in reason.lower()
