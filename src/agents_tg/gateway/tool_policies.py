"""Declarative tool access policies (future: YAML .policy files)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents_tg.services.prompts.tier_rules import PromptTier, tools_for_tier
from src.agents_tg.services.tools.builtin import AgentTool

# Per-agent deny lists (principle of least privilege)
AGENT_TOOL_DENY: dict[str, frozenset[str]] = {
    "personal_assistant": frozenset({"run_code", "deploy_hook", "fetch_url"}),
    "orchestrator": frozenset({"run_code", "deploy_hook"}),
    "research": frozenset({"run_code", "deploy_hook"}),
    "marketing": frozenset({"run_code", "deploy_hook"}),
    "business_manager": frozenset({"run_code", "deploy_hook"}),
    "security_ai": frozenset({"deploy_hook"}),
}

SANDBOX_REQUIRED = frozenset({"run_code", "fetch_url", "deploy_hook"})
SANDBOX_ALLOWED_AGENTS = frozenset({"coder", "orchestrator"})


def _validate_schedule_reminder(args: dict[str, Any]) -> str | None:
    text = str(args.get("text") or args.get("message") or "").strip()
    when = str(args.get("when") or args.get("time") or "").strip()
    if not text:
        return "schedule_reminder: text is required"
    if not when:
        return "schedule_reminder: when/time is required"
    return None


def _validate_obsidian_note(args: dict[str, Any]) -> str | None:
    content = str(
        args.get("content") or args.get("body") or args.get("text") or ""
    ).strip()
    if not content:
        return "create_obsidian_note: content is required"
    return None


def _validate_deploy_hook(args: dict[str, Any]) -> str | None:
    if not str(args.get("hook_url") or args.get("url") or "").strip():
        return "deploy_hook: url is required"
    return None


HIGH_RISK_VALIDATORS: dict[str, Callable[[dict[str, Any]], str | None]] = {
    "schedule_reminder": _validate_schedule_reminder,
    "create_obsidian_note": _validate_obsidian_note,
    "deploy_hook": _validate_deploy_hook,
}


def is_tool_denied_for_agent(agent_key: str, tool_name: str) -> str | None:
    """Return deny reason or None if allowed by agent policy (no args check)."""
    denied = AGENT_TOOL_DENY.get(agent_key, frozenset())
    if tool_name in denied:
        return f"tool {tool_name} not allowed for {agent_key}"

    if tool_name in SANDBOX_REQUIRED and agent_key not in SANDBOX_ALLOWED_AGENTS:
        return f"{tool_name} requires coder agent"

    return None


def is_tool_denied_for_agent_with_args(
    agent_key: str, tool_name: str, args: dict[str, Any]
) -> str | None:
    denied = AGENT_TOOL_DENY.get(agent_key, frozenset())
    if tool_name in denied:
        return f"tool {tool_name} not allowed for {agent_key}"

    if tool_name in SANDBOX_REQUIRED and agent_key not in SANDBOX_ALLOWED_AGENTS:
        return f"{tool_name} requires coder agent"

    validator = HIGH_RISK_VALIDATORS.get(tool_name)
    if validator:
        err = validator(args)
        if err:
            return err
    return None


def is_tool_allowed_for_tier(
    *,
    tool_name: str,
    tier: PromptTier,
    user_message: str,
    include_web_tools: bool,
    registered_tools: list[AgentTool],
) -> bool:
    """Check tool against tier allow-list using tools_for_tier."""
    allowed = tools_for_tier(
        registered_tools,
        tier,
        user_message,
        include_web_tools=include_web_tools,
    )
    return any(t.name == tool_name for t in allowed)
