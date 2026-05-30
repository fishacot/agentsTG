"""Goal-oriented agent loop: tools return data, LLM speaks to the user."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from src.agents_tg.services.agent_prompts import FINALIZE_USER_REPLY
from src.agents_tg.services.agent_identity import get_agent_identity
from src.agents_tg.services.chat_history import chat_history
from src.agents_tg.services.environment_context import AgentEnvironment
from src.agents_tg.services.llm_client import RateLimitError, llm_client
from src.agents_tg.services.memory_service import memory_service
from src.agents_tg.services.prompt_builder import (
    PromptTier,
    build_memory_block,
    build_system_prompt,
    detect_prompt_tier,
    tools_for_tier,
)
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

    MAX_TOOL_ROUNDS = 2
    _RATE_LIMIT_REPLY = (
        "⏳ Сейчас перегрузка AI (лимит Groq). "
        "Подождите 15–30 секунд и повторите."
    )

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

        tier = detect_prompt_tier(user_message, include_web_tools=include_web_tools)
        if tier == PromptTier.LIGHT:
            max_tokens = min(max_tokens, 512)
        elif tier == PromptTier.STANDARD:
            max_tokens = min(max_tokens, 768)

        tool_list = list(tools or [])
        tool_list.append(_remember_tool(agent_key))
        if include_web_tools and tier == PromptTier.FULL:
            tool_list.append(deep_research_tool())

        if environment:
            env_block = environment.to_prompt_block()
        elif environment_block:
            env_block = environment_block
        else:
            env_block = ""

        memory_ctx = await build_memory_block(
            user_message,
            user_id,
            tier,
            memory_service.search,
        )

        history_turns = await chat_history.get_recent(
            user_id,
            agent_key,
            limit=6 if tier == PromptTier.LIGHT else 12,
        )
        history_raw = chat_history.format_for_prompt(history_turns)

        system = build_system_prompt(
            tier=tier,
            human_name=human_name,
            designation=designation,
            soul=soul,
            env_block=env_block,
            history_block=history_raw,
            memory_block=memory_ctx,
            output_hints=output_hints,
            include_web_tools=include_web_tools,
            user_id=user_id,
        )

        active_tools = tools_for_tier(tool_list, tier, user_message)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        openai_tools = [_openai_tool(t) for t in active_tools]
        handlers = {t.name: t.handler for t in tool_list}
        tools_used = False

        try:
            for _ in range(self.MAX_TOOL_ROUNDS):
                try:
                    result = await llm_client.chat_completion(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        agent_key=agent_key,
                        tools=openai_tools if openai_tools else None,
                    )
                except RateLimitError:
                    return self._RATE_LIMIT_REPLY

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
                    args = parse_tool_arguments(fn.get("arguments"), user_id)
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
        except RateLimitError:
            return self._RATE_LIMIT_REPLY

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
        try:
            result = await llm_client.chat_completion(
                finalize_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                agent_key=agent_key,
                tools=None,
            )
        except RateLimitError:
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and (msg.get("content") or "").strip():
                    return str(msg["content"]).strip()
            raise
        text = (result.get("content") or "").strip()
        if text:
            return text
        return await llm_client.chat(
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
    "parse_tool_arguments",
    "tool_result",
]
