"""Manus PlanExecutor — step-by-step plan execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

ProcessFn = Callable[..., Awaitable[str | None]]
DeliverFn = Callable[[Any, str], Awaitable[None]]
ProgressFn = Callable[[int, int, str], Awaitable[None]]


@dataclass
class PlanTask:
    task_id: str
    user_id: int
    title: str
    steps: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class PlanStepView:
    step_index: int
    agent_key: str
    status: str
    instruction: str = ""


@dataclass
class PlanTaskView:
    task_id: str
    status: str
    steps: list[PlanStepView] = field(default_factory=list)


@dataclass
class _PlanResumeHandle:
    task: PlanTask
    message: Any
    user_text: str
    process_fn: ProcessFn
    deliver_fn: DeliverFn | None
    progress_fn: ProgressFn | None


class PlanExecutor:
    """Execute plan steps via gateway agent dispatch."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._factory: async_sessionmaker[AsyncSession] | None = None
        self._memory_tasks: dict[str, dict[str, Any]] = {}
        self._memory_steps: dict[str, list[dict[str, Any]]] = {}
        self._resume_handles: dict[str, _PlanResumeHandle] = {}

    def set_engine(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_task(
        self,
        *,
        telegram_user_id: int,
        title: str,
        steps: list[tuple[str, str]],
        agent_key: str = "orchestrator",
    ) -> PlanTask:
        task_id = uuid4().hex[:16]
        record = {
            "id": task_id,
            "user_id": telegram_user_id,
            "agent_key": agent_key,
            "title": title,
            "status": "planned",
            "context_json": {"plan": [s[1] for s in steps]},
        }
        step_rows = []
        for i, (step_agent, instruction) in enumerate(steps):
            step_rows.append(
                {
                    "id": uuid4().hex[:12],
                    "task_id": task_id,
                    "step_index": i,
                    "agent_key": step_agent,
                    "instruction": instruction,
                    "status": "pending",
                    "result_summary": None,
                }
            )

        if self._factory:
            try:
                from src.agents_tg.db.models import AgentTask, PlanStep

                async with self._factory() as session:
                    session.add(
                        AgentTask(
                            id=task_id,
                            user_id=telegram_user_id,
                            agent_key=agent_key,
                            title=title,
                            status="planned",
                            context_json=record["context_json"],
                        )
                    )
                    for s in step_rows:
                        session.add(
                            PlanStep(
                                id=s["id"],
                                task_id=task_id,
                                step_index=s["step_index"],
                                agent_key=s["agent_key"],
                                instruction=s["instruction"],
                                status="pending",
                            )
                        )
                    await session.commit()
            except Exception as exc:
                logger.warning("PG task create failed: %s", exc)
                self._memory_tasks[task_id] = record
                self._memory_steps[task_id] = step_rows
        else:
            self._memory_tasks[task_id] = record
            self._memory_steps[task_id] = step_rows

        return PlanTask(
            task_id=task_id,
            user_id=telegram_user_id,
            title=title,
            steps=list(steps),
        )

    def register_plan_resume(
        self,
        task_id: str,
        *,
        task: PlanTask,
        message: Any,
        user_text: str,
        process_fn: ProcessFn,
        deliver_fn: DeliverFn | None = None,
        progress_fn: ProgressFn | None = None,
    ) -> None:
        self._resume_handles[task_id] = _PlanResumeHandle(
            task=task,
            message=message,
            user_text=user_text,
            process_fn=process_fn,
            deliver_fn=deliver_fn,
            progress_fn=progress_fn,
        )

    def unregister_plan_resume(self, task_id: str) -> None:
        self._resume_handles.pop(task_id, None)

    async def get_task_context(self, task_id: str) -> dict[str, Any]:
        if self._factory:
            try:
                from src.agents_tg.db.models import AgentTask

                async with self._factory() as session:
                    result = await session.execute(
                        select(AgentTask).where(AgentTask.id == task_id)
                    )
                    row = result.scalar_one_or_none()
                    if row and row.context_json:
                        return dict(row.context_json)
            except Exception as exc:
                logger.debug("PG task context read failed: %s", exc)
        rec = self._memory_tasks.get(task_id)
        if rec:
            return dict(rec.get("context_json") or {})
        return {}

    async def on_a2a_step_callback(
        self,
        task_id: str,
        *,
        step_index: int,
        status: str,
        summary: str = "",
    ) -> dict[str, Any]:
        """Mark external step result; optionally resume in-process plan."""
        normalized = (status or "").lower()
        failed = normalized in ("failed", "error", "cancelled")
        if failed:
            await self._update_step(
                task_id,
                step_index,
                status="failed",
                result_summary=summary[:500] or normalized,
            )
            await self._update_task_status(task_id, "failed")
            return {"ok": True, "resumed": False, "failed": True}

        await self._update_step(
            task_id,
            step_index,
            status="done",
            result_summary=summary[:500] if summary else "a2a ok",
        )
        steps = await self._get_steps(task_id)
        next_index = step_index + 1
        if next_index >= len(steps):
            await self._update_task_status(task_id, "done")
            await self.update_task_context(
                task_id, {"a2a_complete": True, "resume_from_step": None}
            )
            return {"ok": True, "resumed": False, "complete": True}

        await self.update_task_context(
            task_id,
            {
                "a2a_last_completed": step_index,
                "resume_from_step": next_index,
            },
        )
        resumed = await self._try_resume_registered_plan(
            task_id, start_index=next_index
        )
        return {
            "ok": True,
            "resumed": resumed,
            "complete": False,
            "next_step": next_index,
        }

    async def _try_resume_registered_plan(
        self, task_id: str, *, start_index: int
    ) -> bool:
        handle = self._resume_handles.get(task_id)
        if not handle:
            return False
        from src.agents_tg.services.background_runs import background_runs

        async def _resume() -> None:
            try:
                await self.execute_steps_from_index(
                    handle.task,
                    start_index=start_index,
                    message=handle.message,
                    user_text=handle.user_text,
                    process_fn=handle.process_fn,
                    deliver_fn=handle.deliver_fn,
                    progress_fn=handle.progress_fn,
                )
            except Exception as exc:
                logger.exception("Plan resume after A2A failed: %s", exc)

        background_runs.spawn(name=f"plan_a2a_resume_{task_id}", coro_factory=_resume)
        return True

    async def execute_steps_from_index(
        self,
        task: PlanTask,
        *,
        start_index: int,
        message: Any,
        user_text: str,
        process_fn: ProcessFn,
        deliver_fn: DeliverFn | None = None,
        progress_fn: ProgressFn | None = None,
    ) -> str:
        """Run plan steps from start_index (after external A2A completion)."""
        start_index = max(0, start_index)
        results: list[str] = []
        total = len(task.steps)
        from src.agents_tg.services.plan_cancel import clear_cancel, is_cancelled
        from src.agents_tg.services.progress_ux import format_step_done

        for i in range(start_index, total):
            step_agent, instruction = task.steps[i]
            if is_cancelled(task.task_id):
                await self._update_task_status(task.task_id, "cancelled")
                clear_cancel(task.task_id)
                return "⏹ План отменён."
            if progress_fn:
                await progress_fn(i + 1, total, step_agent)
            try:
                result = await self.execute_step(
                    task.task_id,
                    i,
                    message=message,
                    user_text=user_text,
                    process_fn=process_fn,
                    step_agent=step_agent,
                    instruction=instruction,
                )
            except Exception:
                break
            if not result:
                break
            if "[[REPLAN]]" in result:
                return result
            results.append(result)
            if deliver_fn:
                await deliver_fn(message, format_step_done(i + 1, total))
        return results[-1] if results else ""

    async def execute_steps(
        self,
        task: PlanTask,
        *,
        message: Any,
        user_text: str,
        process_fn: ProcessFn,
        deliver_fn: DeliverFn | None = None,
        progress_fn: ProgressFn | None = None,
    ) -> str:
        return await self.execute_steps_from_index(
            task,
            start_index=0,
            message=message,
            user_text=user_text,
            process_fn=process_fn,
            deliver_fn=deliver_fn,
            progress_fn=progress_fn,
        )

    async def execute_step(
        self,
        task_id: str,
        step_index: int,
        *,
        message: Any,
        user_text: str,
        process_fn: ProcessFn,
        step_agent: str | None = None,
        instruction: str | None = None,
    ) -> Optional[str]:
        steps = await self._get_steps(task_id)
        if step_index >= len(steps):
            return None
        step = steps[step_index]
        agent_key = step_agent or step["agent_key"]
        instr = instruction or step["instruction"]
        await self._update_step(task_id, step_index, status="running")
        await self.update_task_context(task_id, {"current_step": step_index})

        prompt = f"[Шаг {step_index + 1}/{len(steps)}] {instr}\n\nКонтекст: {user_text}"

        from src.agents_tg.gateway.agent_dispatch import dispatch_agent
        from src.agents_tg.gateway.envelope import OpenClawEnvelope

        chat = getattr(message, "chat", None)
        from_user = getattr(message, "from_user", None)
        envelope = OpenClawEnvelope(
            chat_id=getattr(chat, "id", 0),
            user_id=getattr(from_user, "id", 0) if from_user else 0,
            text=prompt,
            message_id=getattr(message, "message_id", 0),
            agent_key=agent_key,
            is_group=getattr(chat, "type", "") in ("group", "supergroup"),
        )

        try:
            from src.agents_tg.services.llm_context import set_llm_step_kind

            set_llm_step_kind("plan_step")
            result = await dispatch_agent(
                envelope,
                message=message,
                user_text=prompt,
                coordinator=None,
                task_id=task_id,
            )
            from src.agents_tg.services.progress_ux import strip_supervisor_json_leak
            from src.agents_tg.services.verify_step import verify_step_result

            cleaned = strip_supervisor_json_leak(result or "")
            from src.agents_tg.services.tool_result_buffer import drain

            uid = str(getattr(from_user, "id", 0) if from_user else 0)
            tool_results = drain(uid)
            vr = await verify_step_result(
                instruction=instr,
                step_summary=cleaned,
                agent_key=agent_key,
                tool_results=tool_results or None,
            )
            if not vr.ok:
                await self._update_step(
                    task_id,
                    step_index,
                    status="failed",
                    result_summary=(vr.issues or "verify failed")[:200],
                )
                await self._update_task_status(task_id, "failed")
                if vr.suggest_replan:
                    return f"{cleaned}\n[[REPLAN]]"
                return cleaned

            summary = cleaned[:500]
            await self._update_step(
                task_id, step_index, status="done", result_summary=summary
            )
            status = "done" if step_index + 1 >= len(steps) else "running"
            await self._update_task_status(task_id, status)
            return cleaned
        except Exception as exc:
            logger.exception("Plan step failed: %s", exc)
            await self._update_step(
                task_id, step_index, status="failed", result_summary=str(exc)[:200]
            )
            await self._update_task_status(task_id, "failed")
            raise

    async def get_task(self, task_id: str) -> PlanTaskView | None:
        steps_raw = await self._get_steps(task_id)
        if not steps_raw and task_id not in self._memory_tasks:
            return None
        status = "planned"
        if self._memory_tasks.get(task_id):
            status = self._memory_tasks[task_id].get("status", "planned")
        elif self._factory:
            try:
                from src.agents_tg.db.models import AgentTask

                async with self._factory() as session:
                    result = await session.execute(
                        select(AgentTask).where(AgentTask.id == task_id)
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        status = row.status
            except Exception:
                pass
        steps = [
            PlanStepView(
                step_index=s["step_index"],
                agent_key=s["agent_key"],
                status=s.get("status", "pending"),
                instruction=s.get("instruction", ""),
            )
            for s in steps_raw
        ]
        return PlanTaskView(task_id=task_id, status=status, steps=steps)

    async def save_checkpoint(self, task_id: str, patch: dict[str, Any]) -> None:
        await self.update_task_context(task_id, patch)

    async def update_task_context(self, task_id: str, patch: dict[str, Any]) -> None:
        if self._factory:
            try:
                from src.agents_tg.db.models import AgentTask

                async with self._factory() as session:
                    result = await session.execute(
                        select(AgentTask).where(AgentTask.id == task_id)
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        ctx = dict(row.context_json or {})
                        ctx.update(patch)
                        values: dict[str, Any] = {"context_json": ctx}
                        if "status" in patch:
                            values["status"] = patch["status"]
                        await session.execute(
                            update(AgentTask)
                            .where(AgentTask.id == task_id)
                            .values(**values)
                        )
                        await session.commit()
                        return
            except Exception as exc:
                logger.debug("PG task context update failed: %s", exc)
        if task_id in self._memory_tasks:
            ctx = self._memory_tasks[task_id].get("context_json") or {}
            ctx.update(patch)
            self._memory_tasks[task_id]["context_json"] = ctx

    async def _get_steps(self, task_id: str) -> list[dict[str, Any]]:
        if self._factory:
            try:
                from src.agents_tg.db.models import PlanStep

                async with self._factory() as session:
                    result = await session.execute(
                        select(PlanStep)
                        .where(PlanStep.task_id == task_id)
                        .order_by(PlanStep.step_index)
                    )
                    rows = result.scalars().all()
                    if rows:
                        return [
                            {
                                "id": r.id,
                                "step_index": r.step_index,
                                "agent_key": r.agent_key,
                                "instruction": r.instruction,
                                "status": r.status,
                                "result_summary": r.result_summary,
                            }
                            for r in rows
                        ]
            except Exception as exc:
                logger.debug("PG steps get failed: %s", exc)
        return self._memory_steps.get(task_id, [])

    async def _update_step(
        self,
        task_id: str,
        step_index: int,
        *,
        status: str,
        result_summary: str | None = None,
    ) -> None:
        if self._factory:
            try:
                from src.agents_tg.db.models import PlanStep

                values: dict[str, Any] = {"status": status}
                if result_summary is not None:
                    values["result_summary"] = result_summary
                async with self._factory() as session:
                    await session.execute(
                        update(PlanStep)
                        .where(
                            PlanStep.task_id == task_id,
                            PlanStep.step_index == step_index,
                        )
                        .values(**values)
                    )
                    await session.commit()
                return
            except Exception as exc:
                logger.debug("PG step update failed: %s", exc)
        for s in self._memory_steps.get(task_id, []):
            if s["step_index"] == step_index:
                s["status"] = status
                if result_summary is not None:
                    s["result_summary"] = result_summary

    async def _update_task_status(self, task_id: str, status: str) -> None:
        if self._factory:
            try:
                from src.agents_tg.db.models import AgentTask

                async with self._factory() as session:
                    await session.execute(
                        update(AgentTask)
                        .where(AgentTask.id == task_id)
                        .values(status=status)
                    )
                    await session.commit()
                return
            except Exception as exc:
                logger.debug("PG task status update failed: %s", exc)
        if task_id in self._memory_tasks:
            self._memory_tasks[task_id]["status"] = status


plan_executor = PlanExecutor()
