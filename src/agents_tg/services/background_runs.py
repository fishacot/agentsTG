"""Background agent runs (async research, delegation)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable

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
        ack_text: str = "🔎 Ищу информацию, пришлю результат отдельным сообщением…",
    ) -> str:
        """Return immediate ack; deliver final via deliver_fn."""

        async def _work() -> None:
            result = await process_fn(
                message=message,
                user_text=user_text,
                is_group=False,
                coordinator=None,
            )
            if result:
                await deliver_fn(message, result)

        self.spawn(name="research", coro_factory=_work)
        return ack_text


background_runs = BackgroundRunManager()
