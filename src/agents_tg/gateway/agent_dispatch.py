"""Agent dispatch — L3 entry from gateway (no channel imports)."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.agents_tg.gateway.envelope import OpenClawEnvelope
from src.agents_tg.services.chat_history import chat_history
from src.agents_tg.services.environment_context import build_environment

logger = logging.getLogger(__name__)


def _tool_names_for_agent(agent_key: str) -> list[str]:
    common = [
        "remember_about_user",
        "log_project_activity",
        "update_project_status",
        "list_agent_workspace",
    ]
    if agent_key == "personal_assistant":
        return [
            "create_obsidian_note",
            "post_to_notes_channel",
            "add_task",
            "list_tasks",
            "schedule_reminder",
            "send_telegram_message",
            "update_user_profile",
            "set_active_project",
            *common,
        ]
    if agent_key == "orchestrator":
        return [
            "delegation",
            "delegate_task",
            "track_progress",
            "merge_results",
            "send_telegram_message",
            "update_user_profile",
            "set_active_project",
            *common,
        ]
    if agent_key == "coder":
        return ["run_code", "lint_test", "send_telegram_message", *common]
    if agent_key == "research":
        return [
            "browser_navigate",
            "browser_snapshot",
            "deep_research",
            "send_telegram_message",
            *common,
        ]
    if agent_key == "security_ai":
        return ["scan_prompt", "send_telegram_message", *common]
    return ["deep_research", "send_telegram_message", *common]


async def dispatch_agent(
    envelope: OpenClawEnvelope,
    *,
    message: Any,
    user_text: str,
    coordinator: Any = None,
) -> Optional[str]:
    """Route envelope to the correct agent processor."""
    agent_key = envelope.agent_key
    user_id = str(envelope.user_id) if envelope.user_id else "default"
    is_group = envelope.is_group

    if is_group and coordinator:
        from src.agents_tg.bots.group_coordinator import GroupMessage
        from datetime import datetime, timezone

        coordinator.add_message(
            envelope.chat_id,
            GroupMessage(
                message_id=envelope.message_id,
                from_agent="user",
                text=user_text,
                timestamp=datetime.now(timezone.utc),
                mentions=_extract_mentions(user_text),
            ),
        )

    if is_group and coordinator:
        group_context = coordinator.get_recent_context(envelope.chat_id, 18)
        if group_context:
            user_text = (
                f"Контекст группового чата:\n{group_context}\n\n"
                f"Запрос пользователя: {user_text}"
            )
        dm_recent = ""
    else:
        turns = await chat_history.get_recent(user_id, agent_key)
        dm_recent = chat_history.format_for_prompt(turns)

    environment = await build_environment(
        message=message,
        agent_key=agent_key,
        coordinator=coordinator if is_group else None,
        tool_names=_tool_names_for_agent(agent_key),
        dm_recent=dm_recent,
        group_context_lines=18,
        user_message=user_text,
    )

    from src.agents_tg.services.agent_outer_loop import agent_outer_loop

    return await agent_outer_loop.run(
        agent_key=agent_key,
        user_text=user_text,
        user_id=user_id,
        environment=environment,
    )


def _extract_mentions(text: str) -> list[str]:
    return re.findall(r"@([A-Za-z0-9_]+)", text)


async def dispatch_agent_process(
    *,
    agent_key: str,
    user_text: str,
    user_id: str,
    environment: Any,
    is_group: bool = False,
    coordinator: Any = None,
) -> Optional[str]:
    """Process inbound from agent_bot without channel-layer agent imports."""
    from src.agents_tg.services.agent_outer_loop import agent_outer_loop

    return await agent_outer_loop.run(
        agent_key=agent_key,
        user_text=user_text,
        user_id=user_id,
        environment=environment,
    )
