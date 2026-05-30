"""Async delegation for orchestrator multi-step plans."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from src.agents_tg.services.background_runs import background_runs

logger = logging.getLogger(__name__)

ProcessFn = Callable[..., Awaitable[str | None]]
DeliverFn = Callable[[Any, str], Awaitable[None]]


async def maybe_delegate_async(
    *,
    plan: list[str],
    primary_reply: str,
    message: Any,
    user_text: str,
    process_fn: ProcessFn,
    deliver_fn: DeliverFn,
) -> str:
    """If plan has 2+ steps, notify user and finish remaining work in background."""
    if len(plan) < 2:
        return primary_reply

    suffix = (
        "\n\n⏳ План из нескольких шагов — выполню остальное "
        "и пришлю итог отдельным сообщением."
    )
    base = primary_reply if primary_reply else f"<b>План:</b>\n" + "\n".join(
        f"{i + 1}. {s}" for i, s in enumerate(plan)
    )

    async def _work() -> None:
        try:
            final = await process_fn(
                message=message,
                user_text=user_text,
                is_group=True,
                coordinator=None,
            )
            if final and final.strip() != primary_reply.strip():
                await deliver_fn(message, final)
        except Exception as exc:
            logger.exception("Orchestrator async delegation failed: %s", exc)
            await deliver_fn(
                message,
                "😕 Не удалось завершить все шаги плана. Попробуйте уточнить запрос.",
            )

    background_runs.spawn(name="orchestrator_delegate", coro_factory=_work)
    return base + suffix
