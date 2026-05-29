"""Goal-oriented agent loop: tools return data, LLM speaks to the user."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from src.agents_tg.services.agent_prompts import (
    FINALIZE_USER_REPLY,
    GOAL_DIRECTIVE,
    WEB_TOOL_HINT,
)
from src.agents_tg.services.agent_identity import get_agent_identity
from src.agents_tg.services.memory_service import memory_service
from src.agents_tg.services.qwen_client import qwen_client
from src.agents_tg.utils.internet import fetch_web_page, web_search

logger = logging.getLogger(__name__)

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


def _openai_tool(tool: AgentTool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


async def _memory_block(user_message: str, user_id: str) -> str:
    memories = await memory_service.search(user_message, user_id=user_id, limit=8)
    if not memories:
        return (
            "\n\nПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ:\n"
            "Пока нет сохранённых фактов. Можешь запоминать через remember_about_user, "
            "когда пользователь сообщает что-то важное о себе.\n"
        )
    lines = []
    for item in memories:
        text = item.get("text") or item.get("memory") or ""
        if text:
            lines.append(f"- {text}")
    if not lines:
        return ""
    return "\n\nПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ:\n" + "\n".join(lines)


def _remember_tool(agent_key: str) -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        fact = str(kwargs.get("fact", "")).strip()
        user_id = str(kwargs.get("user_id", "default"))
        if not fact:
            return tool_result(ok=False, error="empty_fact")
        await memory_service.add(
            fact,
            user_id=user_id,
            metadata={"agent": agent_key},
        )
        return tool_result(ok=True, stored=fact)

    return AgentTool(
        name="remember_about_user",
        description=(
            "Сохранить факт о пользователе. Только когда он сообщает информацию о себе, "
            "не на вопросы «ты помнишь?» / «можешь запоминать?»."
        ),
        parameters={
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "Краткий факт о пользователе",
                },
            },
            "required": ["fact"],
        },
        handler=handler,
    )


def web_tools() -> list[AgentTool]:
    async def search_handler(**kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return tool_result(ok=False, error="empty_query")
        results = await web_search(query, max_results=5)
        if not results:
            return tool_result(ok=True, results=[])
        compact = []
        for row in results:
            compact.append(
                {
                    "title": row.get("title") or "",
                    "url": row.get("href") or row.get("url") or "",
                    "snippet": (row.get("body") or "")[:280],
                }
            )
        return tool_result(ok=True, results=compact)

    async def fetch_handler(**kwargs: Any) -> str:
        url = str(kwargs.get("url", "")).strip()
        if not url:
            return tool_result(ok=False, error="empty_url")
        content = await fetch_web_page(url)
        if not content or content.startswith("Failed"):
            return tool_result(ok=False, error="fetch_failed", url=url)
        return tool_result(ok=True, url=url, content=content[:3000])

    return [
        AgentTool(
            name="web_search",
            description="Поиск в интернете, когда нужны актуальные данные или ссылки.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"},
                },
                "required": ["query"],
            },
            handler=search_handler,
        ),
        AgentTool(
            name="fetch_web_page",
            description="Загрузить текст страницы по URL для анализа.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Полный URL страницы"},
                },
                "required": ["url"],
            },
            handler=fetch_handler,
        ),
    ]


class AgentRunner:
    """Run an agent: understand the goal, use tools only when needed."""

    MAX_TOOL_ROUNDS = 3

    async def run(
        self,
        *,
        agent_key: str,
        soul: str,
        user_message: str,
        user_id: str = "default",
        tools: list[AgentTool] | None = None,
        output_hints: str = "",
        include_web_tools: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 900,
    ) -> str:
        identity = get_agent_identity(agent_key)
        human_name = identity.get("human_name") or agent_key
        designation = identity.get("designation") or ""

        tool_list = list(tools or [])
        tool_list.append(_remember_tool(agent_key))
        if include_web_tools:
            tool_list.extend(web_tools())

        memory_ctx = await _memory_block(user_message, user_id)
        hints = f"\n\n{output_hints}" if output_hints else ""
        web_hint = f"\n\n{WEB_TOOL_HINT}" if include_web_tools else ""

        system = (
            f"{GOAL_DIRECTIVE}\n\n"
            f"Ты — **{human_name}**, {designation}.\n\n"
            f"{soul}{memory_ctx}{web_hint}{hints}\n\n"
            f"user_id для инструментов: {user_id}"
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        openai_tools = [_openai_tool(t) for t in tool_list]
        handlers = {t.name: t.handler for t in tool_list}
        tools_used = False

        for _ in range(self.MAX_TOOL_ROUNDS):
            result = await qwen_client.chat_completion(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                agent_key=agent_key,
                tools=openai_tools if openai_tools else None,
            )
            tool_calls = result.get("tool_calls") or []
            content = (result.get("content") or "").strip()

            if not tool_calls:
                if content:
                    return content
                if tools_used:
                    break
                return (
                    "Не смог ответить — попробуй переформулировать "
                    "или задай вопрос проще."
                )

            tools_used = True
            messages.append(
                {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": tool_calls,
                }
            )

            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
                args.setdefault("user_id", user_id)
                handler = handlers.get(name)
                if not handler:
                    tool_output = tool_result(ok=False, error=f"unknown_tool:{name}")
                else:
                    try:
                        tool_output = await handler(**args)
                    except Exception as exc:
                        logger.exception("Tool %s failed", name)
                        tool_output = tool_result(ok=False, error=str(exc))

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", name),
                        "content": tool_output,
                    }
                )

        return await self._finalize_user_message(
            messages,
            agent_key=agent_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _finalize_user_message(
        self,
        messages: list[dict[str, Any]],
        *,
        agent_key: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Force a natural-language reply after tool observations."""
        finalize_messages = list(messages)
        finalize_messages.append({"role": "system", "content": FINALIZE_USER_REPLY})
        result = await qwen_client.chat_completion(
            finalize_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_key=agent_key,
            tools=None,
        )
        text = (result.get("content") or "").strip()
        if text:
            return text
        return await qwen_client.chat(
            finalize_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_key=agent_key,
        )


agent_runner = AgentRunner()

__all__ = ["AgentRunner", "AgentTool", "agent_runner", "tool_result", "web_tools"]
