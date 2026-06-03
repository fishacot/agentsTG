"""Async delegation for orchestrator multi-step plans (Manus executor)."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from src.agents_tg.services.background_runs import background_runs
from src.agents_tg.services.delegation_envelope import DelegationEnvelope
from src.agents_tg.services.plan_executor import plan_executor

logger = logging.getLogger(__name__)

ProcessFn = Callable[..., Awaitable[str | None]]
DeliverFn = Callable[..., Awaitable[None]]

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

    from src.agents_tg.config.settings import get_settings

    max_steps = max(2, int(get_settings().MAX_PLAN_STEPS or 4))
    if len(plan) > max_steps:
        plan = plan[:max_steps]

    from src.agents_tg.services.progress_ux import (
        format_handoff,
        format_plan_header,
        format_step_progress,
        strip_supervisor_json_leak,
    )

    suffix = "\n\n⏳ План из нескольких шагов — статус обновлю в одном сообщении."
    safe_reply = strip_supervisor_json_leak(primary_reply) if primary_reply else ""
    base = safe_reply if safe_reply else format_plan_header(plan)

    from_user = getattr(message, "from_user", None)
    uid = from_user.id if from_user else 0

    from src.agents_tg.services.plan_recipe_service import plan_recipe_service

    recipe = None
    if uid:
        recipe = await plan_recipe_service.find_by_intent(
            user_id=uid, intent_sample=user_text
        )
        if (
            recipe
            and isinstance(recipe.steps_json, list)
            and len(recipe.steps_json) >= 2
        ):
            parsed_steps: list[tuple[str, str]] = []
            for item in recipe.steps_json[:max_steps]:
                if isinstance(item, dict):
                    ak = str(item.get("agent_key") or "research")
                    instr = str(item.get("instruction") or "")
                    if instr:
                        parsed_steps.append((ak, instr))
            if len(parsed_steps) >= 2:
                steps = parsed_steps
                suffix += (
                    f"\n\n<i>Шаблон плана (×{recipe.success_count}) — "
                    f"подходит под запрос.</i>"
                )
            else:
                steps = [(_guess_agent_for_step(s), s) for s in plan]
        else:
            steps = [(_guess_agent_for_step(s), s) for s in plan]
    else:
        steps = [(_guess_agent_for_step(s), s) for s in plan]
    task = await plan_executor.create_task(
        telegram_user_id=uid,
        title=user_text[:200],
        steps=steps,
    )
    first_agent = steps[0][0] if steps else "research"
    envelope = DelegationEnvelope.from_plan_step(
        task_id=task.task_id,
        requester_user_id=uid,
        target_agent_id=first_agent,
        instruction=steps[0][1] if steps else user_text[:500],
        user_text=user_text,
    )
    await plan_executor.update_task_context(
        task.task_id,
        {
            "delegation": envelope.to_dict(),
            "telegram_chat_id": getattr(getattr(message, "chat", None), "id", 0),
            "telegram_user_id": uid,
            "plan_user_text": user_text[:2000],
        },
    )

    prev_agent = agent_key
    plan_steps_snapshot = list(steps)

    from src.agents_tg.services.plan_progress import PlanProgressTracker

    progress_tracker = PlanProgressTracker(message, task_id=task.task_id)

    async def _progress(current: int, total: int, step_agent: str) -> None:
        nonlocal prev_agent
        if step_agent != prev_agent and current > 1:
            step_text = steps[current - 1][1] if current - 1 < len(steps) else ""
            await deliver_fn(
                message,
                format_handoff(
                    from_agent=prev_agent,
                    to_agent=step_agent,
                    instruction=step_text,
                ),
                reply_to_message_id=getattr(message, "message_id", None),
            )
            prev_agent = step_agent
        header = format_plan_header([instr for _, instr in plan_steps_snapshot])
        progress_text = format_step_progress(current, total, step_agent)
        await progress_tracker.update(
            f"{header}\n\n{progress_text}",
            show_cancel=(current == 1),
        )
        if current == 1:
            prev_agent = step_agent

    async def _work() -> None:
        from src.agents_tg.services.agent_runtime import OutboundSink, set_outbound_sink

        plan_executor.register_plan_resume(
            task.task_id,
            task=task,
            message=message,
            user_text=user_text,
            process_fn=process_fn,
            deliver_fn=deliver_fn,
            progress_fn=_progress,
        )
        sink = OutboundSink(coalesce_idle_ms=0, preview_enabled=False)
        set_outbound_sink(sink)
        try:
            final = await plan_executor.execute_steps(
                task,
                message=message,
                user_text=user_text,
                process_fn=process_fn,
                deliver_fn=deliver_fn,
                progress_fn=_progress,
            )
            if (
                uid
                and final
                and "отменён" not in final.lower()
                and "[[REPLAN]]" not in final
            ):
                await plan_recipe_service.save_recipe(
                    user_id=uid,
                    intent_sample=user_text,
                    steps_json=[
                        {"agent_key": ak, "instruction": instr}
                        for ak, instr in plan_steps_snapshot
                    ],
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
        finally:
            for conf in sink.drain_confirmations():
                await deliver_fn(
                    message,
                    conf.text,
                    reply_markup=conf.reply_markup,
                    reply_to_message_id=getattr(message, "message_id", None),
                )
            set_outbound_sink(None)
            plan_executor.unregister_plan_resume(task.task_id)

    background_runs.spawn(name="orchestrator_plan_exec", coro_factory=_work)
    return base + suffix
