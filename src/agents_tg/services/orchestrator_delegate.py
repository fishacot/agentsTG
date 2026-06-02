"""Async delegation for orchestrator multi-step plans (Manus executor)."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from src.agents_tg.services.background_runs import background_runs
from src.agents_tg.services.plan_executor import plan_executor

logger = logging.getLogger(__name__)

ProcessFn = Callable[..., Awaitable[str | None]]
DeliverFn = Callable[[Any, str], Awaitable[None]]

# Map plan step text hints → specialist agent_key
_STEP_AGENT_HINTS: list[tuple[str, str]] = [
    ("поиск", "research"),
    ("найди", "research"),
    ("код", "coder"),
    ("разработ", "coder"),
    ("безопас", "security_ai"),
    ("маркет", "marketing"),
    ("бизнес", "business_manager"),
    ("задач", "personal_assistant"),
    ("напомин", "personal_assistant"),
]


def _guess_agent_for_step(step_text: str) -> str:
    low = step_text.lower()
    for hint, agent_key in _STEP_AGENT_HINTS:
        if hint in low:
            return agent_key
    return "research"


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
    """If plan has 2+ steps, execute via PlanExecutor in background."""
    if len(plan) < 2:
        return primary_reply

    from src.agents_tg.services.progress_ux import (
        format_plan_header,
        format_step_progress,
        strip_supervisor_json_leak,
    )

    suffix = (
        "\n\n⏳ План из нескольких шагов — выполню по шагам "
        "и пришлю прогресс отдельными сообщениями."
    )
    safe_reply = strip_supervisor_json_leak(primary_reply) if primary_reply else ""
    base = safe_reply if safe_reply else format_plan_header(plan)

    from_user = getattr(message, "from_user", None)
    uid = from_user.id if from_user else 0

    steps = [(_guess_agent_for_step(s), s) for s in plan]
    task = await plan_executor.create_task(
        telegram_user_id=uid,
        title=user_text[:200],
        steps=steps,
    )

    async def _progress(current: int, total: int, step_agent: str) -> None:
        await deliver_fn(message, format_step_progress(current, total, step_agent))

    async def _work() -> None:
        try:
            final = await plan_executor.execute_steps(
                task,
                message=message,
                user_text=user_text,
                process_fn=process_fn,
                deliver_fn=deliver_fn,
                progress_fn=_progress,
            )
            if final and final.strip() != primary_reply.strip():
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
            logger.exception("Orchestrator plan execution failed: %s", exc)
            err = "😕 Не удалось завершить все шаги плана. Попробуйте уточнить запрос."
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

    background_runs.spawn(name="orchestrator_plan_exec", coro_factory=_work)
    return base + suffix
