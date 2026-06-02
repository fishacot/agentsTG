"""Goal-oriented agent loop: tools return data, LLM speaks to the user."""

from __future__ import annotations

import logging
from typing import Any

from src.agents_tg.services.agent_delivery_profile import get_delivery_profile
from src.agents_tg.services.prompts.finalize_directives import build_finalize_prompt
from src.agents_tg.services.agent_runtime import get_outbound_sink
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
from src.agents_tg.services.prompts.identity import prompt_identity
from src.agents_tg.services.tools.builtin import (
    AgentTool,
    deep_research_tool,
    openai_tool,
    parse_tool_arguments,
    remember_tool,
    send_telegram_message_tool,
    tool_result,
)

logger = logging.getLogger(__name__)


class AgentRunner:
    """Run an agent: understand the goal, use tools only when needed."""

    MAX_TOOL_ROUNDS = 1
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
        max_tool_rounds_override: int | None = None,
    ) -> str:
        human_name, designation = prompt_identity(agent_key)

        profile = get_delivery_profile(agent_key)
        max_tool_rounds = max_tool_rounds_override or profile.max_tool_rounds

        tier = detect_prompt_tier(user_message, include_web_tools=include_web_tools)
        profile_cap = profile.max_tokens
        if tier == PromptTier.LIGHT:
            max_tokens = min(max_tokens, profile_cap, 512)
        elif tier == PromptTier.STANDARD:
            max_tokens = min(max_tokens, profile_cap, 640)
        else:
            max_tokens = min(max_tokens, profile_cap)

        tool_list = list(tools or [])
        tool_list.append(remember_tool(agent_key))
        from src.agents_tg.services.role_tools import role_tools_for
        from src.agents_tg.services.shared_context_tools import shared_context_tools

        tool_list.extend(role_tools_for(agent_key))
        tool_list.extend(shared_context_tools(agent_key=agent_key))
        if get_outbound_sink() is not None:
            tool_list.append(send_telegram_message_tool())
        if include_web_tools:
            tool_list.append(deep_research_tool())

        from src.agents_tg.services.tools.registry import tool_names_for_agent

        if environment and not environment.tool_names:
            environment.tool_names = tool_names_for_agent(agent_key)

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
            limit=4 if tier == PromptTier.LIGHT else (8 if tier == PromptTier.STANDARD else 12),
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
            user_message=user_message,
        )

        from src.agents_tg.gateway.hook_registry import hook_registry

        system, block_reason = await hook_registry.run_before_prompt_build(
            agent_key=agent_key,
            user_id=user_id,
            user_message=user_message,
            system=system,
        )
        if block_reason:
            return block_reason

        active_tools = tools_for_tier(
            tool_list, tier, user_message, include_web_tools=include_web_tools
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        openai_tools = [openai_tool(t) for t in active_tools]
        handlers = {t.name: t.handler for t in tool_list}
        tool_hook_context = {
            "tier": tier,
            "user_message": user_message,
            "include_web_tools": include_web_tools,
            "registered_tools": tool_list,
        }
        tools_used = False

        try:
            for _ in range(max_tool_rounds):
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
                        allowed, reason = await hook_registry.run_before_tool_call(
                            agent_key=agent_key,
                            user_id=user_id,
                            tool_name=name,
                            args=args,
                            context=tool_hook_context,
                        )
                        if not allowed:
                            tool_output = tool_result(ok=False, error=reason or "denied")
                        else:
                            try:
                                tool_output = await handler(**args)
                            except Exception as exc:
                                logger.exception("Tool %s failed", name)
                                tool_output = tool_result(ok=False, error=str(exc))
                                await hook_registry.run_after_tool_exec(
                                    agent_key=agent_key,
                                    user_id=user_id,
                                    tool_name=name,
                                    args=args,
                                    output="",
                                    error=str(exc),
                                    context=tool_hook_context,
                                )
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": call.get("id", name),
                                        "content": tool_output,
                                    }
                                )
                                continue
                        await hook_registry.run_after_tool_exec(
                            agent_key=agent_key,
                            user_id=user_id,
                            tool_name=name,
                            args=args,
                            output=tool_output,
                            context=tool_hook_context,
                        )

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
                tools_used=tools_used,
            )
            final = await self._maybe_continue(
                messages,
                final,
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
        tools_used: bool = False,
    ) -> str:
        """Force a natural-language reply after tool observations."""
        finalize_messages = list(messages)
        finalize_messages.append(
            {
                "role": "system",
                "content": build_finalize_prompt(has_tool_results=tools_used),
            }
        )
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

    async def _maybe_continue(
        self,
        messages: list[dict[str, Any]],
        text: str,
        *,
        agent_key: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """One continuation if the model hit output length during finalize."""
        if not text or len(text) < max_tokens // 2:
            return text
        continue_messages = list(messages)
        continue_messages.append({"role": "assistant", "content": text})
        continue_messages.append(
            {
                "role": "user",
                "content": "Продолжи ответ с места обрыва. Не повторяй уже сказанное.",
            }
        )
        try:
            result = await llm_client.chat_completion(
                continue_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                agent_key=agent_key,
                tools=None,
            )
        except RateLimitError:
            return text
        extra = (result.get("content") or "").strip()
        if not extra:
            return text
        if result.get("finish_reason") == "length" and len(extra) > 100:
            return text + "\n\n" + extra + "\n\n<i>(ответ сокращён — уточните детали)</i>"
        return text + "\n\n" + extra


agent_runner = AgentRunner()

__all__ = [
    "AgentRunner",
    "AgentTool",
    "agent_runner",
    "deep_research_tool",
    "parse_tool_arguments",
    "tool_result",
]
