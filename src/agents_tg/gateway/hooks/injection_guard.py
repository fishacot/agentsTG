"""Injection guard and tool audit hooks."""

from __future__ import annotations

import re
from typing import Any

from src.agents_tg.gateway.tool_policies import is_tool_denied_for_agent_with_args
from src.agents_tg.utils.structured_log import log_event

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"disregard\s+(your\s+)?(system|safety)", re.I),
    re.compile(r"you\s+are\s+now\s+(DAN|jailbreak)", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
]


async def before_prompt_injection_guard(
    *,
    agent_key: str,
    user_id: str,
    user_message: str,
    system: str,
) -> dict[str, Any] | None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(user_message):
            log_event(
                "injection_blocked",
                agent=agent_key,
                user_id=user_id,
                pattern=pattern.pattern,
            )
            return {
                "block": True,
                "reason": (
                    "Запрос содержит подозрительные инструкции. "
                    "Переформулируйте задачу без override system prompt."
                ),
            }
    return None


async def before_tool_sandbox_guard(
    *,
    agent_key: str,
    user_id: str,
    tool_name: str,
    args: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    deny = is_tool_denied_for_agent_with_args(agent_key, tool_name, args)
    if deny:
        return {"deny": True, "reason": deny}
    return None


async def after_tool_audit(
    *,
    agent_key: str,
    user_id: str,
    tool_name: str,
    args: dict[str, Any],
    output: str,
    error: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    ctx = context or {}
    event = "tool_error" if error else "tool_call"
    log_event(
        event,
        agent=agent_key,
        user_id=user_id,
        tool=tool_name,
        error=error,
        tier=ctx.get("tier"),
    )
    uid = int(user_id) if user_id.isdigit() else 0
    if uid:
        from src.agents_tg.services.workspace_memory import append_journal_md

        append_journal_md(
            uid,
            agent_key=agent_key,
            event=event,
            payload={
                "tool": tool_name,
                "error": error,
                "ok": error is None,
                "tier": str(ctx.get("tier", "")),
            },
        )


INJECTION_PATTERNS = _INJECTION_PATTERNS
