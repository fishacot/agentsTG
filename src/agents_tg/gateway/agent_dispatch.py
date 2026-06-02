"""Agent dispatch — L3 entry from gateway (no channel imports)."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.agents_tg.gateway.envelope import OpenClawEnvelope
from src.agents_tg.services.chat_history import chat_history
from src.agents_tg.services.environment_context import build_environment
from src.agents_tg.services.tools.registry import tool_names_for_agent

logger = logging.getLogger(__name__)


async def dispatch_agent(
    envelope: OpenClawEnvelope,
    *,
    message: Any,
    user_text: str,
    coordinator: Any = None,
) -> Optional[str]:
    """Route envelope to the correct agent processor (single L3 entry)."""
    agent_key = envelope.agent_key
    user_id = str(envelope.user_id) if envelope.user_id else "default"
    is_group = envelope.is_group

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
        tool_names=tool_names_for_agent(agent_key),
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
