"""Tools to write owner NOTEBOOK.md (external memory)."""

from __future__ import annotations

from typing import Any

from src.agents_tg.services.notebook import append_notebook
from src.agents_tg.services.tools.builtin import AgentTool, tool_result


def append_notebook_tool(agent_key: str) -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = kwargs.get("user_id") or kwargs.get("telegram_user_id")
        if not uid:
            return tool_result(ok=False, error="missing_user_id")
        text = str(kwargs.get("text") or "").strip()
        result = append_notebook(
            int(uid) if str(uid).isdigit() else uid,
            text=text,
            agent_key=agent_key,
        )
        return tool_result(**result)

    return AgentTool(
        name="append_notebook",
        description=(
            "Добавить строку в NOTEBOOK.md владельца (внешняя память). "
            "Используй для итогов задачи, решений, контекста — чтобы не дублировать в чат."
        ),
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Краткая заметка"},
            },
            "required": ["text"],
        },
        handler=handler,
    )
