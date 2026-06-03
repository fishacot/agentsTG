"""Agent runtime: turn-based execution with outbound message sink."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from aiogram.types import Message

from src.agents_tg.channels.delivery.streaming import PreviewStreamer
from src.agents_tg.gateway.coalesce import BlockCoalescer

logger = logging.getLogger(__name__)

SILENT_REPLY = "NO_REPLY"


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


class TriggerKind(str, Enum):
    INBOUND = "inbound"
    CRON = "cron"
    DELEGATION = "delegation"
    BACKGROUND = "background"


@dataclass
class OutboundConfirmation:
    """Inline confirmation UI to deliver after the run."""

    text: str
    reply_markup: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    """Result of an agent run — one or more outbound messages."""

    messages: list[str] = field(default_factory=list)
    confirmations: list[OutboundConfirmation] = field(default_factory=list)
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


def _build_outbound_sink(
    *,
    thinking_message: Message | None = None,
) -> OutboundSink:
    from src.agents_tg.config.settings import get_settings

    settings = get_settings()
    coalesce_ms = settings.COALESCE_IDLE_MS if settings.COALESCE_IDLE_MS > 0 else 0
    preview = settings.PREVIEW_STREAMING_ENABLED and thinking_message is not None
    return OutboundSink(
        coalesce_idle_ms=coalesce_ms,
        preview_enabled=preview,
        preview_message=thinking_message,
    )


class OutboundSink:
    """Collects outbound messages during a run (coalesce + optional live preview)."""

    def __init__(
        self,
        *,
        coalesce_idle_ms: int = 0,
        preview_enabled: bool = False,
        preview_message: Message | None = None,
    ) -> None:
        self._coalescer: BlockCoalescer | None = (
            BlockCoalescer(idle_ms=coalesce_idle_ms) if coalesce_idle_ms > 0 else None
        )
        self._preview: PreviewStreamer | None = None
        if preview_enabled and preview_message is not None:
            self._preview = PreviewStreamer(preview_message)
        self._messages: list[str] = []
        self._confirmations: list[OutboundConfirmation] = []

    def push_confirmation(self, text: str, reply_markup: dict[str, Any]) -> None:
        self._confirmations.append(
            OutboundConfirmation(text=text, reply_markup=reply_markup)
        )

    def drain_confirmations(self) -> list[OutboundConfirmation]:
        items = list(self._confirmations)
        self._confirmations.clear()
        return items

    async def push(self, text: str) -> None:
        cleaned = (text or "").strip()
        if cleaned and cleaned.upper() not in (SILENT_REPLY, "NO_REPLY"):
            if self._coalescer is not None:
                self._coalescer.push(cleaned, _now_ms())
                if self._preview is not None:
                    await self._preview.update(self._coalescer.preview_text)
            else:
                self._messages.append(cleaned)
                if self._preview is not None:
                    await self._preview.update("\n\n".join(self._messages))

    def drain_messages(self) -> list[str]:
        """Committed blocks after coalesce flush, or direct pushes."""
        if self._coalescer is not None:
            return self._coalescer.flush()
        return list(self._messages)

    @property
    def messages(self) -> list[str]:
        return self.drain_messages()

    async def finalize_preview(self, text: str | None = None) -> None:
        if self._preview is None:
            return
        body = text or ""
        if not body and self._coalescer is not None:
            body = self._coalescer.preview_text
        elif not body and self._messages:
            body = "\n\n".join(self._messages)
        if body:
            await self._preview.finalize(body)

    def clear(self) -> None:
        if self._coalescer is not None:
            self._coalescer.flush()
        self._messages.clear()


# ContextVar-style global for current run sink (set per inbound turn)
_current_sink: OutboundSink | None = None


def get_outbound_sink() -> OutboundSink | None:
    return _current_sink


def set_outbound_sink(sink: OutboundSink | None) -> None:
    global _current_sink
    _current_sink = sink


ProcessFn = Callable[..., Awaitable[str | None]]


def _merge_run_messages(sink: OutboundSink, reply: str | None) -> list[str]:
    messages = sink.drain_messages()
    if reply and reply.strip():
        cleaned = reply.strip()
        if not messages or messages[-1] != cleaned:
            messages.append(cleaned)
    return messages


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
        thinking_message: Message | None = None,
    ) -> AgentRunResult:
        del agent_key, is_group  # reserved for future per-agent delivery profiles
        sink = _build_outbound_sink(thinking_message=thinking_message)
        set_outbound_sink(sink)
        try:
            from src.agents_tg.services.llm_cooldown import llm_cooldown

            user_id = str(message.from_user.id) if message.from_user else "default"
            from src.agents_tg.services.llm_context import set_llm_user_id

            set_llm_user_id(user_id)
            from src.agents_tg.services.llm_budget import llm_budget

            if await llm_budget.is_exhausted(user_id):
                used, limit = await llm_budget.get_usage(user_id)
                return AgentRunResult(
                    messages=[
                        f"📓 Дневной лимит AI ({used}/{limit}) исчерпан. "
                        "Завтра сбросится; важное — в NOTEBOOK или «запомни …»."
                    ]
                )
            allowed, wait_sec = await llm_cooldown.check(user_id)
            if not allowed:
                from src.agents_tg.utils.structured_log import log_event

                log_event("llm_cooldown", user_id=user_id, wait_sec=wait_sec)
                return AgentRunResult(
                    messages=[f"⏳ Подождите {wait_sec} сек. (лимит запросов к AI)."]
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

            messages = _merge_run_messages(sink, reply)
            await sink.finalize_preview(messages[0] if messages else None)

            if not messages and not sink._confirmations:
                return AgentRunResult(messages=[])

            return AgentRunResult(
                messages=messages,
                confirmations=sink.drain_confirmations(),
            )
        finally:
            set_outbound_sink(None)

    async def run_scheduled(
        self,
        *,
        agent_key: str,
        telegram_user_id: int,
        chat_id: int,
        user_text: str,
        trigger: TriggerKind,
        process_fn: ProcessFn,
        coordinator: Any = None,
        skip_cooldown: bool = True,
    ) -> AgentRunResult:
        """Proactive agent turn (cron, heartbeat, event wake) without inbound message."""
        from types import SimpleNamespace

        sink = _build_outbound_sink(thinking_message=None)
        set_outbound_sink(sink)
        try:
            from src.agents_tg.utils.structured_log import log_event

            log_event(
                "scheduled_start",
                agent=agent_key,
                user_id=telegram_user_id,
                chat_id=chat_id,
                trigger=trigger.value,
            )

            from src.agents_tg.services.llm_context import set_llm_user_id

            set_llm_user_id(str(telegram_user_id))
            if not skip_cooldown:
                from src.agents_tg.services.llm_cooldown import llm_cooldown

                user_id = str(telegram_user_id)
                allowed, wait_sec = await llm_cooldown.check(user_id)
                if not allowed:
                    log_event("llm_cooldown", user_id=user_id, wait_sec=wait_sec)
                    return AgentRunResult(silent=True)

            message = SimpleNamespace(
                chat=SimpleNamespace(id=chat_id, type="private"),
                from_user=SimpleNamespace(id=telegram_user_id, username=None),
            )

            reply = await process_fn(
                message=message,
                user_text=user_text,
                is_group=False,
                coordinator=coordinator,
            )

            if not skip_cooldown:
                from src.agents_tg.services.llm_cooldown import llm_cooldown

                await llm_cooldown.record(str(telegram_user_id))

            if reply and reply.strip().upper() in (
                SILENT_REPLY,
                "NO_REPLY",
                "HEARTBEAT_OK",
            ):
                return AgentRunResult(silent=True)

            messages = _merge_run_messages(sink, reply)

            if not messages and not sink._confirmations:
                return AgentRunResult(messages=[])

            return AgentRunResult(
                messages=messages,
                confirmations=sink.drain_confirmations(),
            )
        finally:
            set_outbound_sink(None)


agent_runtime = AgentRuntime()
