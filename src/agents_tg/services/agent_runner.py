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
    TELEGRAM_AGENT_PROTOCOL,
    TELEGRAM_HTML_FORMAT,
    WEB_TOOL_HINT,
)
from src.agents_tg.services.agent_identity import get_agent_identity
from src.agents_tg.services.chat_history import chat_history
from src.agents_tg.services.environment_context import AgentEnvironment
from src.agents_tg.services.memory_service import memory_service
from src.agents_tg.services.qwen_client import qwen_client
from src.agents_tg.services.search_provider import deep_research

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
            "Пока нет сохранённых фактов. Используй remember_about_user, "
            "когда пользователь сообщает факт о себе.\n"
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
        environment: AgentEnvironment | None = None,
        environment_block: str = "",
        temperature: float = 0.4,
        max_tokens: int = 900,
    ) -> str:
        identity = get_agent_identity(agent_key)
        human_name = identity.get("human_name") or agent_key
        designation = identity.get("designation") or ""

        tool_list = list(tools or [])
        tool_list.append(_remember_tool(agent_key))
        if include_web_tools:
            tool_list.append(deep_research_tool())

        tool_names = [t.name for t in tool_list]
        if environment:
            env_block = environment.to_prompt_block()
        elif environment_block:
            env_block = environment_block
        else:
            env_block = ""

        memory_ctx = await _memory_block(user_message, user_id)
        hints = f"\n\n{output_hints}" if output_hints else ""
        web_hint = f"\n\n{WEB_TOOL_HINT}" if include_web_tools else ""

        history_turns = await chat_history.get_recent(user_id, agent_key)
        history_block = chat_history.format_for_prompt(history_turns)
        if history_block:
            history_block = f"\n\n## НЕДАВНИЙ ДИАЛОГ\n{history_block}\n"

        system = (
            f"{GOAL_DIRECTIVE}\n\n"
            f"{TELEGRAM_AGENT_PROTOCOL}\n\n"
            f"{TELEGRAM_HTML_FORMAT}\n\n"
            f"Ты — <b>{human_name}</b>, {designation}.\n\n"
            f"{soul}{env_block}{history_block}{memory_ctx}{web_hint}{hints}\n\n"
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
                    await chat_history.append(user_id, agent_key, "user", user_message)
                    await chat_history.append(user_id, agent_key, "assistant", content)
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

        final = await self._finalize_user_message(
            messages,
            agent_key=agent_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        await chat_history.append(user_id, agent_key, "user", user_message)
        await chat_history.append(user_id, agent_key, "assistant", final)
        return final

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

__all__ = [
    "AgentRunner",
    "AgentTool",
    "agent_runner",
    "deep_research_tool",
    "tool_result",
]
