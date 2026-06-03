"""Gateway router — dispatch envelope to session + job."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.agents_tg.gateway.envelope import OpenClawEnvelope
from src.agents_tg.gateway.job_store import job_store
from src.agents_tg.gateway.session import session_manager
from src.agents_tg.services.message_pipeline import message_pipeline

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    session_id: str
    job_id: str
    duplicate: bool = False
    envelope: OpenClawEnvelope | None = None


class GatewayRouter:
    """L2 stateless router: envelope → session + job record."""

    async def dispatch(
        self,
        envelope: OpenClawEnvelope,
        *,
        trigger: str = "inbound",
    ) -> DispatchResult:
        if await message_pipeline.is_duplicate(
            envelope.agent_key, envelope.chat_id, envelope.message_id
        ):
            existing_key = envelope.idempotency_key
            existing_job_id = job_store.get_by_idempotency(existing_key)
            session_id = session_manager.get_or_create(
                envelope.user_id, envelope.agent_key
            )
            return DispatchResult(
                session_id=session_id,
                job_id=existing_job_id or "",
                duplicate=True,
                envelope=envelope.with_session(session_id),
            )

        session_id = session_manager.get_or_create(envelope.user_id, envelope.agent_key)
        job = await job_store.create(
            user_id=envelope.user_id,
            agent_key=envelope.agent_key,
            trigger=trigger,
            payload=envelope.to_job_payload(),
            idempotency_key=envelope.idempotency_key,
            status="queued",
        )
        bound = envelope.with_session(session_id)
        logger.debug(
            "Gateway dispatch agent=%s session=%s job=%s",
            envelope.agent_key,
            session_id,
            job["id"],
        )
        return DispatchResult(
            session_id=session_id,
            job_id=job["id"],
            duplicate=False,
            envelope=bound,
        )

    async def start_job(self, job_id: str) -> None:
        """Transition queued → running when processing begins."""
        if job_id:
            await job_store.transition(job_id, "running")

    async def complete_job(
        self,
        job_id: str,
        *,
        status: str = "done",
        result_summary: str | None = None,
    ) -> None:
        if job_id:
            await job_store.transition(job_id, status, result_summary=result_summary)

    async def fail_job(
        self,
        job_id: str,
        *,
        result_summary: str | None = None,
    ) -> None:
        if job_id:
            await job_store.transition(job_id, "failed", result_summary=result_summary)

    async def handle_a2a_callback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """A2A webhook — job completion + optional delegation step callback."""
        job_id = str(payload.get("job_id", ""))
        status = str(payload.get("status", "done"))
        summary = payload.get("result_summary")
        task_id = str(payload.get("task_id", ""))
        step_index = payload.get("step_index")
        if not job_id:
            return {"ok": False, "error": "missing job_id"}
        job = await job_store.get(job_id)
        if not job:
            return {"ok": False, "error": "job_not_found"}
        await job_store.transition(
            job_id, status, result_summary=str(summary) if summary else None
        )
        plan_result: dict[str, Any] | None = None
        if task_id and step_index is not None:
            from src.agents_tg.services.plan_executor import plan_executor

            ctx_patch: dict[str, Any] = {
                "a2a_callback": {
                    "job_id": job_id,
                    "step_index": step_index,
                    "status": status,
                    "summary": str(summary)[:500] if summary else "",
                },
                "current_step": int(step_index),
            }
            await plan_executor.update_task_context(task_id, ctx_patch)
            plan_result = await plan_executor.on_a2a_step_callback(
                task_id,
                step_index=int(step_index),
                status=status,
                summary=str(summary) if summary else "",
            )
            if plan_result and not plan_result.get("resumed"):
                ctx = await plan_executor.get_task_context(task_id)
                chat_id = int(ctx.get("telegram_chat_id") or 0)
                user_id = int(ctx.get("telegram_user_id") or 0)
                if chat_id and user_id and plan_result.get("complete"):
                    try:
                        from src.agents_tg.services.agent_runtime import TriggerKind
                        from src.agents_tg.services.agent_wake import agent_wake_service

                        await agent_wake_service.run_event_wake(
                            agent_key="orchestrator",
                            telegram_user_id=user_id,
                            chat_id=chat_id,
                            prompt="",
                            trigger=TriggerKind.DELEGATION,
                            precomputed="✅ План завершён (внешний шаг A2A).",
                        )
                    except Exception as exc:
                        logger.debug("A2A plan complete notify failed: %s", exc)
        return {
            "ok": True,
            "job_id": job_id,
            "status": status,
            "task_id": task_id or None,
            "plan": plan_result,
        }


gateway_router = GatewayRouter()
