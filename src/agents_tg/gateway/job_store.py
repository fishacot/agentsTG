"""Agent job store — PG + in-memory fallback."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

JOB_STATUSES = frozenset(
    {"queued", "running", "waiting_confirm", "done", "failed", "cancelled"}
)

JOB_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"done", "failed", "waiting_confirm", "cancelled"}),
    "waiting_confirm": frozenset({"running", "done", "failed", "cancelled"}),
    "done": frozenset(),
    "failed": frozenset({"queued"}),
    "cancelled": frozenset(),
}


class AgentJobStore:
    """CRUD for agent_jobs table."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._factory: async_sessionmaker[AsyncSession] | None = None
        self._memory: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, str] = {}

    def set_engine(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._factory = async_sessionmaker(engine, expire_on_commit=False)

    def get_by_idempotency(self, key: str) -> str | None:
        return self._idempotency.get(key)

    async def create(
        self,
        *,
        user_id: int,
        agent_key: str,
        trigger: str = "inbound",
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        status: str = "queued",
    ) -> dict[str, Any]:
        if idempotency_key:
            existing = self.get_by_idempotency(idempotency_key)
            if existing:
                job = await self.get(existing)
                if job:
                    return job

        job_id = uuid4().hex[:16]
        now = datetime.now(timezone.utc)
        record = {
            "id": job_id,
            "user_id": user_id,
            "agent_key": agent_key,
            "status": status,
            "trigger": trigger,
            "payload": payload or {},
            "idempotency_key": idempotency_key or "",
            "created_at": now,
            "updated_at": now,
        }

        if self._factory:
            try:
                from src.agents_tg.db.models import AgentJob

                async with self._factory() as session:
                    row = AgentJob(
                        id=job_id,
                        user_id=user_id,
                        agent_key=agent_key,
                        status=status,
                        trigger=trigger,
                        payload=payload or {},
                        idempotency_key=idempotency_key or "",
                    )
                    session.add(row)
                    await session.commit()
            except Exception as exc:
                logger.warning("PG job create failed, using memory: %s", exc)
                self._memory[job_id] = record
        else:
            self._memory[job_id] = record

        if idempotency_key:
            self._idempotency[idempotency_key] = job_id
        return record

    async def get(self, job_id: str) -> dict[str, Any] | None:
        if self._factory:
            try:
                from src.agents_tg.db.models import AgentJob

                async with self._factory() as session:
                    result = await session.execute(
                        select(AgentJob).where(AgentJob.id == job_id)
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        return self._row_to_dict(row)
            except Exception as exc:
                logger.debug("PG job get failed: %s", exc)
        return self._memory.get(job_id)

    def can_transition(self, current: str, new_status: str) -> bool:
        if new_status not in JOB_STATUSES:
            return False
        allowed = JOB_TRANSITIONS.get(current, frozenset())
        return new_status in allowed or current == new_status

    async def transition(
        self,
        job_id: str,
        new_status: str,
        *,
        result_summary: str | None = None,
    ) -> bool:
        """Apply FSM transition; returns False if job missing or transition invalid."""
        job = await self.get(job_id)
        if not job:
            logger.warning("Job transition skipped — not found: %s", job_id)
            return False
        current = job.get("status", "queued")
        if not self.can_transition(current, new_status):
            logger.warning(
                "Invalid job transition %s: %s → %s",
                job_id,
                current,
                new_status,
            )
            return False
        await self.update_status(job_id, new_status, result_summary=result_summary)
        return True

    async def update_status(
        self,
        job_id: str,
        status: str,
        *,
        result_summary: str | None = None,
    ) -> None:
        if status not in JOB_STATUSES:
            raise ValueError(f"invalid status: {status}")

        if self._factory:
            try:
                from src.agents_tg.db.models import AgentJob

                values: dict[str, Any] = {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
                if result_summary is not None:
                    values["result_summary"] = result_summary
                async with self._factory() as session:
                    await session.execute(
                        update(AgentJob).where(AgentJob.id == job_id).values(**values)
                    )
                    await session.commit()
                return
            except Exception as exc:
                logger.debug("PG job update failed: %s", exc)

        if job_id in self._memory:
            self._memory[job_id]["status"] = status
            self._memory[job_id]["updated_at"] = datetime.now(timezone.utc)
            if result_summary is not None:
                self._memory[job_id]["result_summary"] = result_summary

    async def list_by_status(
        self, status: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        if self._factory:
            try:
                from src.agents_tg.db.models import AgentJob

                async with self._factory() as session:
                    result = await session.execute(
                        select(AgentJob)
                        .where(AgentJob.status == status)
                        .order_by(AgentJob.created_at.desc())
                        .limit(limit)
                    )
                    return [self._row_to_dict(r) for r in result.scalars()]
            except Exception as exc:
                logger.debug("PG job list failed: %s", exc)
        return [j for j in self._memory.values() if j.get("status") == status][:limit]

    async def recover_on_startup(self) -> int:
        """Re-queue running jobs after crash."""
        stuck = await self.list_by_status("running", limit=100)
        for job in stuck:
            await self.update_status(job["id"], "queued")
        return len(stuck)

    recover_stale = recover_on_startup

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "agent_key": row.agent_key,
            "status": row.status,
            "trigger": row.trigger,
            "payload": row.payload or {},
            "idempotency_key": row.idempotency_key or "",
            "result_summary": getattr(row, "result_summary", None),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }


job_store = AgentJobStore()
