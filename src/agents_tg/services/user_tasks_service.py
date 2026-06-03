"""Persist user to-do items (PG with in-memory fallback)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class _MemTask:
    id: int
    telegram_user_id: int
    title: str
    due_date: str | None
    status: str


class UserTasksService:
    """CRUD for user tasks."""

    def __init__(self) -> None:
        self._memory: dict[int, list[_MemTask]] = {}
        self._next_id = 1
        self._pg_engine: Any | None = None

    def set_pg_engine(self, engine: Any) -> None:
        self._pg_engine = engine

    async def add_task(
        self,
        *,
        telegram_user_id: int,
        title: str,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        title = title.strip()
        if not title:
            return {"ok": False, "error": "empty_title"}

        if self._pg_engine:
            tid = await self._insert_pg(telegram_user_id, title, due_date)
        else:
            tid = self._next_id
            self._next_id += 1
            bucket = self._memory.setdefault(telegram_user_id, [])
            bucket.append(
                _MemTask(
                    id=tid,
                    telegram_user_id=telegram_user_id,
                    title=title,
                    due_date=due_date,
                    status="pending",
                )
            )

        pending = await self.list_tasks(telegram_user_id=telegram_user_id)
        return {
            "ok": True,
            "id": tid,
            "title": title,
            "due_date": due_date,
            "total_tasks": len(pending.get("tasks") or []),
        }

    async def _insert_pg(
        self, telegram_user_id: int, title: str, due_date: str | None
    ) -> int:
        from sqlalchemy import insert

        from src.agents_tg.db.models import UserTask

        async with self._pg_engine.begin() as conn:
            result = await conn.execute(
                insert(UserTask)
                .values(
                    telegram_user_id=telegram_user_id,
                    title=title,
                    due_date=due_date,
                    status="pending",
                )
                .returning(UserTask.id)
            )
            row = result.first()
            return int(row[0])

    async def list_tasks(
        self, *, telegram_user_id: int, status: str = "pending"
    ) -> dict[str, Any]:
        if self._pg_engine:
            tasks = await self._list_pg(telegram_user_id, status)
        else:
            tasks = [
                {
                    "id": t.id,
                    "title": t.title,
                    "due_date": t.due_date,
                    "status": t.status,
                }
                for t in self._memory.get(telegram_user_id, [])
                if t.status == status
            ]
        return {"ok": True, "tasks": tasks}

    async def _list_pg(
        self, telegram_user_id: int, status: str
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from src.agents_tg.db.models import UserTask

        async with self._pg_engine.connect() as conn:
            rows = await conn.execute(
                select(UserTask).where(
                    UserTask.telegram_user_id == telegram_user_id,
                    UserTask.status == status,
                )
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "due_date": r.due_date,
                    "status": r.status,
                }
                for r in rows.scalars().all()
            ]


user_tasks_service = UserTasksService()
