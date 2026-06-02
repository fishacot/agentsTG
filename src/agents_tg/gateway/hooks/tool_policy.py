"""Deterministic tool policy hook (tier + agent deny + high-risk args)."""

from __future__ import annotations

from typing import Any

from src.agents_tg.gateway.tool_policies import (
    is_tool_allowed_for_tier,
    is_tool_denied_for_agent_with_args,
)
from src.agents_tg.services.prompts.tier_rules import PromptTier
from src.agents_tg.services.tools.builtin import AgentTool
from src.agents_tg.utils.structured_log import log_event


async def before_tool_policy_guard(
    *,
    agent_key: str,
    user_id: str,
    tool_name: str,
    args: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    ctx = context or {}
    deny = is_tool_denied_for_agent_with_args(agent_key, tool_name, args)
    if deny:
        log_event(
            "tool_policy_deny",
            agent=agent_key,
            user_id=user_id,
            tool=tool_name,
            reason=deny,
            tier=ctx.get("tier"),
        )
        return {"deny": True, "reason": deny}

    tier_raw = ctx.get("tier")
    if tier_raw is None:
        return None

    tier = tier_raw if isinstance(tier_raw, PromptTier) else PromptTier(str(tier_raw))
    registered: list[AgentTool] = ctx.get("registered_tools") or []
    user_message = str(ctx.get("user_message") or "")
    include_web = bool(ctx.get("include_web_tools"))

    if registered and not is_tool_allowed_for_tier(
        tool_name=tool_name,
        tier=tier,
        user_message=user_message,
        include_web_tools=include_web,
        registered_tools=registered,
    ):
        reason = f"tool {tool_name} not allowed for tier {tier.value}"
        log_event(
            "tool_policy_deny",
            agent=agent_key,
            user_id=user_id,
            tool=tool_name,
            reason=reason,
            tier=tier.value,
        )
        return {"deny": True, "reason": reason}

    return None
