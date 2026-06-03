"""Background agent runs (async research, delegation)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ProcessFn = Callable[..., Awaitable[str | None]]
DeliverFn = Callable[[Any, str], Awaitable[None]]


class BackgroundRunManager:
    """Run long agent tasks without blocking the inbound handler."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def spawn(
        self,
        *,
        name: str,
        coro_factory: Callable[[], Awaitable[None]],
    ) -> None:
        async def _wrapper() -> None:
            try:
                await coro_factory()
            except Exception as exc:
                logger.exception("Background run %s failed: %s", name, exc)

        task = asyncio.create_task(_wrapper(), name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def run_research_background(
        self,
        *,
        message: Any,
        user_text: str,
        process_fn: ProcessFn,
        deliver_fn: DeliverFn,
        agent_key: str = "research",
        ack_text: str = "🔎 Ищу информацию, пришлю результат отдельным сообщением…",
    ) -> str:
        """Return immediate ack; deliver final via event wake + runtime tracking."""

        async def _work() -> None:
            result = await process_fn(
                message=message,
                user_text=user_text,
                is_group=False,
                coordinator=None,
            )
            if not result:
                return
            from_user = getattr(message, "from_user", None)
            if from_user:
                from src.agents_tg.services.agent_runtime import TriggerKind
                from src.agents_tg.services.agent_wake import agent_wake_service

                await agent_wake_service.run_event_wake(
                    agent_key=agent_key,
                    telegram_user_id=from_user.id,
                    chat_id=message.chat.id,
                    prompt="",
                    trigger=TriggerKind.BACKGROUND,
                    precomputed=result,
                )
            else:
                await deliver_fn(message, result)

        self.spawn(name="research", coro_factory=_work)
        return ack_text


background_runs = BackgroundRunManager()
