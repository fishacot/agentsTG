"""OpenClaw security hooks registry."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

BeforePromptFn = Callable[..., Awaitable[dict[str, Any] | None]]
BeforeToolFn = Callable[..., Awaitable[dict[str, Any] | None]]
AfterToolFn = Callable[..., Awaitable[None]]


class HookRegistry:
    """Ordered hook execution for gateway security parity."""

    def __init__(self) -> None:
        self._before_prompt: list[BeforePromptFn] = []
        self._before_tool: list[BeforeToolFn] = []
        self._after_tool: list[AfterToolFn] = []

    def register_before_prompt(self, fn: BeforePromptFn) -> None:
        self._before_prompt.append(fn)

    def register_before_tool(self, fn: BeforeToolFn) -> None:
        self._before_tool.append(fn)

    def register_after_tool(self, fn: AfterToolFn) -> None:
        self._after_tool.append(fn)

    async def run_before_prompt_build(
        self,
        *,
        agent_key: str,
        user_id: str,
        user_message: str,
        system: str,
    ) -> tuple[str, str | None]:
        current_system = system
        for hook in self._before_prompt:
            result = await hook(
                agent_key=agent_key,
                user_id=user_id,
                user_message=user_message,
                system=current_system,
            )
            if not result:
                continue
            if result.get("block"):
                return current_system, str(result.get("reason", "blocked"))
            if "system" in result:
                current_system = str(result["system"])
        return current_system, None

    async def run_before_tool_call(
        self,
        *,
        agent_key: str,
        user_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> tuple[bool, str | None]:
        for hook in self._before_tool:
            result = await hook(
                agent_key=agent_key,
                user_id=user_id,
                tool_name=tool_name,
                args=args,
            )
            if result and result.get("deny"):
                return False, str(result.get("reason", "denied"))
        return True, None

    async def run_after_tool_exec(
        self,
        *,
        agent_key: str,
        user_id: str,
        tool_name: str,
        args: dict[str, Any],
        output: str,
        error: str | None = None,
    ) -> None:
        for hook in self._after_tool:
            try:
                await hook(
                    agent_key=agent_key,
                    user_id=user_id,
                    tool_name=tool_name,
                    args=args,
                    output=output,
                    error=error,
                )
            except Exception as exc:
                logger.warning("after_tool hook failed: %s", exc)

    async def run_before_prompt(
        self,
        *,
        agent_key: str,
        user_message: str,
        context: dict[str, Any],
    ) -> tuple[str, bool]:
        user_id = str(context.get("user_id", "default"))
        _, block = await self.run_before_prompt_build(
            agent_key=agent_key,
            user_id=user_id,
            user_message=user_message,
            system="",
        )
        return user_message, bool(block)

    async def run_before_tool(
        self,
        *,
        agent_key: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> tuple[bool, str | None]:
        user_id = str(args.get("user_id", "default"))
        return await self.run_before_tool_call(
            agent_key=agent_key,
            user_id=user_id,
            tool_name=tool_name,
            args=args,
        )

    async def run_after_tool(
        self,
        *,
        agent_key: str,
        tool_name: str,
        args: dict[str, Any],
        output: str,
        error: str | None = None,
    ) -> None:
        user_id = str(args.get("user_id", "default"))
        await self.run_after_tool_exec(
            agent_key=agent_key,
            user_id=user_id,
            tool_name=tool_name,
            args=args,
            output=output,
            error=error,
        )


hook_registry = HookRegistry()
