"""Built-in LLM tools shared across agents."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from src.agents_tg.services.agent_runtime import get_outbound_sink
from src.agents_tg.services.memory_service import memory_service
from src.agents_tg.services.search_provider import deep_research

ToolHandler = Callable[..., Awaitable[str]]


def tool_result(**payload: Any) -> str:
    """Machine-readable tool output for the LLM (never shown raw to the user)."""
    return json.dumps(payload, ensure_ascii=False)


@dataclass(frozen=True)
class AgentTool:
    """LLM-callable tool with async handler."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler


def openai_tool(tool: AgentTool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def parse_tool_arguments(raw_args: str | None, user_id: str) -> dict[str, Any]:
    """Parse Groq/OpenAI tool arguments; Groq may return JSON null."""
    payload = raw_args or "{}"
    try:
        parsed = json.loads(payload)
        args = parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        args = {}
    args.setdefault("user_id", user_id)
    return args


def send_telegram_message_tool() -> AgentTool:
    """Allow agent to push an intermediate user-visible message during a run."""

    async def handler(**kwargs: Any) -> str:
        text = str(kwargs.get("text", "")).strip()
        if not text:
            return tool_result(ok=False, error="empty_text")
        sink = get_outbound_sink()
        if sink is None:
            return tool_result(ok=False, error="no_active_run")
        sink.push(text)
        return tool_result(ok=True, queued=True, length=len(text))

    return AgentTool(
        name="send_telegram_message",
        description=(
            "Отправить промежуточное сообщение пользователю в Telegram "
            "(статус, «ищу…», уточнение). Финальный ответ всё равно сформулируй."
        ),
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст для пользователя (HTML)"},
            },
            "required": ["text"],
        },
        handler=handler,
    )


def remember_tool(agent_key: str) -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        fact = str(kwargs.get("fact", "")).strip()
        user_id = str(kwargs.get("user_id", "default"))
        category = str(kwargs.get("category", "identity")).strip() or "identity"
        if not fact:
            return tool_result(ok=False, error="empty_fact")
        await memory_service.add(
            fact,
            user_id=user_id,
            metadata={"agent": agent_key, "category": category},
        )
        return tool_result(ok=True, stored=fact, category=category)

    return AgentTool(
        name="remember_about_user",
        description=(
            "Сохранить факт о пользователе (общая память всех агентов). "
            "category: identity | preference | project. "
            "Только когда он сообщает информацию о себе."
        ),
        parameters={
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "Краткий факт о пользователе",
                },
                "category": {
                    "type": "string",
                    "enum": ["identity", "preference", "project"],
                    "description": "Тип факта",
                },
            },
            "required": ["fact"],
        },
        handler=handler,
    )


def deep_research_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return tool_result(ok=False, error="empty_query")
        extra = kwargs.get("extra_queries") or []
        if isinstance(extra, str):
            extra = [extra]
        data = await deep_research(query, extra_queries=list(extra)[:2])
        return tool_result(**data)

    return AgentTool(
        name="deep_research",
        description=(
            "Глубокий поиск в интернете: результаты + содержимое топ-страниц. "
            "Используй когда нужны актуальные данные, ссылки, сравнение решений."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Основной поисковый запрос"},
                "extra_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Дополнительные запросы (0-2) для сложной темы",
                },
            },
            "required": ["query"],
        },
        handler=handler,
    )


__all__ = [
    "AgentTool",
    "ToolHandler",
    "deep_research_tool",
    "openai_tool",
    "parse_tool_arguments",
    "remember_tool",
    "send_telegram_message_tool",
    "tool_result",
]
