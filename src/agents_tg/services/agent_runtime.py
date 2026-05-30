"""Agent runtime: turn-based execution with outbound message sink."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Awaitable

if TYPE_CHECKING:
    from aiogram.types import Message

logger = logging.getLogger(__name__)

SILENT_REPLY = "NO_REPLY"


class TriggerKind(str, Enum):
    INBOUND = "inbound"
    CRON = "cron"
    DELEGATION = "delegation"
    BACKGROUND = "background"


@dataclass
class AgentRunResult:
    """Result of an agent run — one or more outbound messages."""

    messages: list[str] = field(default_factory=list)
    silent: bool = False

    @property
    def primary(self) -> str | None:
        if self.silent or not self.messages:
            return None
        return self.messages[0]

    @property
    def extras(self) -> list[str]:
        if self.silent or len(self.messages) <= 1:
            return []
        return self.messages[1:]


class OutboundSink:
    """Collects outbound messages during a run (multi-bubble)."""

    def __init__(self) -> None:
        self._messages: list[str] = []

    def push(self, text: str) -> None:
        cleaned = (text or "").strip()
        if cleaned and cleaned.upper() not in (SILENT_REPLY, "NO_REPLY"):
            self._messages.append(cleaned)

    @property
    def messages(self) -> list[str]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()


# ContextVar-style global for current run sink (set per inbound turn)
_current_sink: OutboundSink | None = None


def get_outbound_sink() -> OutboundSink | None:
    return _current_sink


def set_outbound_sink(sink: OutboundSink | None) -> None:
    global _current_sink
    _current_sink = sink


ProcessFn = Callable[..., Awaitable[str | None]]


class AgentRuntime:
    """Execute agent logic and merge sink + final reply."""

    async def run_inbound(
        self,
        *,
        agent_key: str,
        process_fn: ProcessFn,
        message: Message,
        user_text: str,
        is_group: bool,
        coordinator: Any,
    ) -> AgentRunResult:
        sink = OutboundSink()
        set_outbound_sink(sink)
        try:
            from src.agents_tg.services.llm_cooldown import llm_cooldown

            user_id = str(message.from_user.id) if message.from_user else "default"
            allowed, wait_sec = await llm_cooldown.check(user_id)
            if not allowed:
                from src.agents_tg.utils.structured_log import log_event

                log_event("llm_cooldown", user_id=user_id, wait_sec=wait_sec)
                return AgentRunResult(
                    messages=[
                        f"⏳ Подождите {wait_sec} сек. (лимит запросов к AI)."
                    ]
                )

            reply = await process_fn(
                message=message,
                user_text=user_text,
                is_group=is_group,
                coordinator=coordinator,
            )
            await llm_cooldown.record(user_id)

            if reply and reply.strip().upper() in (SILENT_REPLY, "NO_REPLY"):
                return AgentRunResult(silent=True)

            messages = sink.messages
            if reply and reply.strip():
                if not messages or messages[-1] != reply.strip():
                    messages.append(reply.strip())

            if not messages:
                return AgentRunResult(messages=[])

            return AgentRunResult(messages=messages)
        finally:
            set_outbound_sink(None)


agent_runtime = AgentRuntime()
