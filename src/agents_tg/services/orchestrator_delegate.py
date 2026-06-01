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
    agent_key: str = "orchestrator",
) -> str:
    """If plan has 2+ steps, notify user and finish remaining work in background."""
    if len(plan) < 2:
        return primary_reply

    suffix = (
        "\n\n⏳ План из нескольких шагов — выполню остальное "
        "и пришлю итог отдельным сообщением."
    )
    base = primary_reply if primary_reply else "<b>План:</b>\n" + "\n".join(
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
                from_user = getattr(message, "from_user", None)
                if from_user:
                    from src.agents_tg.services.agent_runtime import TriggerKind
                    from src.agents_tg.services.agent_wake import agent_wake_service

                    await agent_wake_service.run_event_wake(
                        agent_key=agent_key,
                        telegram_user_id=from_user.id,
                        chat_id=message.chat.id,
                        prompt="",
                        trigger=TriggerKind.DELEGATION,
                        precomputed=final,
                    )
                else:
                    await deliver_fn(message, final)
        except Exception as exc:
            logger.exception("Orchestrator async delegation failed: %s", exc)
            err = "😕 Не удалось завершить все шаги плана. Попробуйте уточнить запрос."
            from_user = getattr(message, "from_user", None)
            if from_user:
                from src.agents_tg.services.agent_runtime import TriggerKind
                from src.agents_tg.services.agent_wake import agent_wake_service

                await agent_wake_service.run_event_wake(
                    agent_key=agent_key,
                    telegram_user_id=from_user.id,
                    chat_id=message.chat.id,
                    prompt="",
                    trigger=TriggerKind.DELEGATION,
                    precomputed=err,
                )
            else:
                await deliver_fn(message, err)

    background_runs.spawn(name="orchestrator_delegate", coro_factory=_work)
    return base + suffix
