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

        session_id = session_manager.get_or_create(
            envelope.user_id, envelope.agent_key
        )
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

    async def complete_job(
        self,
        job_id: str,
        *,
        status: str = "done",
        result_summary: str | None = None,
    ) -> None:
        if job_id:
            await job_store.update_status(job_id, status, result_summary=result_summary)

    async def handle_a2a_callback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """A2A webhook stub — mark job done from external agent."""
        job_id = str(payload.get("job_id", ""))
        status = str(payload.get("status", "done"))
        summary = payload.get("result_summary")
        if not job_id:
            return {"ok": False, "error": "missing job_id"}
        job = await job_store.get(job_id)
        if not job:
            return {"ok": False, "error": "job_not_found"}
        await job_store.update_status(
            job_id, status, result_summary=str(summary) if summary else None
        )
        return {"ok": True, "job_id": job_id, "status": status}


gateway_router = GatewayRouter()
