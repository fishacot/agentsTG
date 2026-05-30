"""Shared user profile, project focus, and cross-agent activity journal."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

ACTIVITY_KINDS = frozenset(
    {"research", "code", "plan", "note", "delegation", "marketing", "security"}
)
PROJECT_STATUSES = frozenset({"active", "paused", "done"})


@dataclass
class _MemProfile:
    telegram_user_id: int
    display_name: str | None = None
    address_as: str | None = None
    bio: str | None = None
    preferences_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class _MemProject:
    id: int
    telegram_user_id: int
    title: str
    description: str | None = None
    status: str = "active"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _MemActivity:
    id: int
    project_id: int
    telegram_user_id: int
    agent_key: str
    kind: str
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SharedContextService:
    """OpenClaw-style shared USER + FOCUS for all 7 agents."""

    def __init__(self) -> None:
        self._pg_engine: Any | None = None
        self._profiles: dict[int, _MemProfile] = {}
        self._projects: dict[int, _MemProject] = {}
        self._activities: list[_MemActivity] = []
        self._next_project_id = 1
        self._next_activity_id = 1

    def set_pg_engine(self, engine: Any) -> None:
        self._pg_engine = engine

    async def get_profile(self, telegram_user_id: int) -> dict[str, Any]:
        if self._pg_engine:
            return await self._get_profile_pg(telegram_user_id)
        p = self._profiles.get(telegram_user_id)
        if not p:
            return {}
        return {
            "telegram_user_id": telegram_user_id,
            "display_name": p.display_name,
            "address_as": p.address_as,
            "bio": p.bio,
            "preferences": p.preferences_json or {},
        }

    async def update_profile(
        self,
        telegram_user_id: int,
        *,
        display_name: str | None = None,
        address_as: str | None = None,
        bio: str | None = None,
        likes: list[str] | None = None,
        dislikes: list[str] | None = None,
        style: str | None = None,
    ) -> dict[str, Any]:
        prefs: dict[str, Any] = {}
        if self._pg_engine:
            existing = await self._get_profile_pg(telegram_user_id)
            prefs = dict(existing.get("preferences") or {})
        else:
            p = self._profiles.get(telegram_user_id)
            if p:
                prefs = dict(p.preferences_json or {})

        if likes is not None:
            prefs["likes"] = likes
        if dislikes is not None:
            prefs["dislikes"] = dislikes
        if style is not None:
            prefs["style"] = style

        if self._pg_engine:
            await self._upsert_profile_pg(
                telegram_user_id,
                display_name=display_name,
                address_as=address_as,
                bio=bio,
                preferences_json=prefs or None,
            )
        else:
            p = self._profiles.get(telegram_user_id)
            if p is None:
                p = _MemProfile(telegram_user_id=telegram_user_id)
                self._profiles[telegram_user_id] = p
            if display_name is not None:
                p.display_name = display_name
            if address_as is not None:
                p.address_as = address_as
            if bio is not None:
                p.bio = bio
            p.preferences_json = prefs

        return await self.get_profile(telegram_user_id)

    async def get_active_project(self, telegram_user_id: int) -> dict[str, Any] | None:
        if self._pg_engine:
            return await self._get_active_project_pg(telegram_user_id)
        active = [
            p
            for p in self._projects.values()
            if p.telegram_user_id == telegram_user_id and p.status == "active"
        ]
        if not active:
            return None
        p = max(active, key=lambda x: x.updated_at)
        return {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "status": p.status,
        }

    async def set_active_project(
        self,
        telegram_user_id: int,
        *,
        title: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("empty_title")

        if self._pg_engine:
            return await self._set_active_project_pg(
                telegram_user_id, title=title, description=description
            )

        for p in self._projects.values():
            if p.telegram_user_id == telegram_user_id and p.status == "active":
                p.status = "paused"

        pid = self._next_project_id
        self._next_project_id += 1
        now = datetime.now(timezone.utc)
        self._projects[pid] = _MemProject(
            id=pid,
            telegram_user_id=telegram_user_id,
            title=title,
            description=description,
            status="active",
            updated_at=now,
        )
        return {"id": pid, "title": title, "description": description, "status": "active"}

    async def update_project_status(
        self,
        telegram_user_id: int,
        *,
        project_id: int | None = None,
        status: str,
    ) -> dict[str, Any]:
        if status not in PROJECT_STATUSES:
            raise ValueError(f"invalid_status:{status}")

        if self._pg_engine:
            return await self._update_project_status_pg(
                telegram_user_id, project_id=project_id, status=status
            )

        target = None
        if project_id:
            target = self._projects.get(project_id)
        else:
            for p in self._projects.values():
                if p.telegram_user_id == telegram_user_id and p.status == "active":
                    target = p
                    break
        if not target or target.telegram_user_id != telegram_user_id:
            return {"ok": False, "error": "project_not_found"}
        target.status = status
        target.updated_at = datetime.now(timezone.utc)
        return {"ok": True, "id": target.id, "status": status}

    async def log_activity(
        self,
        telegram_user_id: int,
        *,
        agent_key: str,
        summary: str,
        kind: str = "note",
        project_id: int | None = None,
    ) -> dict[str, Any]:
        summary = summary.strip()[:500]
        if not summary:
            return {"ok": False, "error": "empty_summary"}
        kind = kind if kind in ACTIVITY_KINDS else "note"

        project = await self.get_active_project(telegram_user_id)
        pid = project_id or (project["id"] if project else None)
        if pid is None:
            return {"ok": False, "error": "no_active_project"}

        if self._pg_engine:
            return await self._log_activity_pg(
                telegram_user_id,
                project_id=pid,
                agent_key=agent_key,
                summary=summary,
                kind=kind,
            )

        aid = self._next_activity_id
        self._next_activity_id += 1
        self._activities.append(
            _MemActivity(
                id=aid,
                project_id=pid,
                telegram_user_id=telegram_user_id,
                agent_key=agent_key,
                kind=kind,
                summary=summary,
            )
        )
        if pid in self._projects:
            self._projects[pid].updated_at = datetime.now(timezone.utc)
        return {"ok": True, "id": aid, "project_id": pid}

    async def get_recent_activity(
        self,
        telegram_user_id: int,
        *,
        project_id: int | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        if self._pg_engine:
            return await self._get_recent_activity_pg(
                telegram_user_id, project_id=project_id, limit=limit
            )

        project = await self.get_active_project(telegram_user_id)
        pid = project_id or (project["id"] if project else None)
        if pid is None:
            return []

        rows = [
            a
            for a in self._activities
            if a.telegram_user_id == telegram_user_id and a.project_id == pid
        ]
        rows.sort(key=lambda x: x.created_at, reverse=True)
        return [
            {
                "agent_key": a.agent_key,
                "kind": a.kind,
                "summary": a.summary,
                "created_at": a.created_at.isoformat(),
            }
            for a in rows[:limit]
        ]

    # --- Postgres ---

    async def _get_profile_pg(self, telegram_user_id: int) -> dict[str, Any]:
        from sqlalchemy import select

        from src.agents_tg.db.models import UserProfile

        async with self._pg_engine.connect() as conn:
            row = await conn.execute(
                select(UserProfile).where(
                    UserProfile.telegram_user_id == telegram_user_id
                )
            )
            p = row.scalar_one_or_none()
            if not p:
                return {}
            return {
                "telegram_user_id": telegram_user_id,
                "display_name": p.display_name,
                "address_as": p.address_as,
                "bio": p.bio,
                "preferences": p.preferences_json or {},
            }

    async def _upsert_profile_pg(
        self,
        telegram_user_id: int,
        *,
        display_name: str | None,
        address_as: str | None,
        bio: str | None,
        preferences_json: dict | None,
    ) -> None:
        from sqlalchemy import select

        from src.agents_tg.db.models import UserProfile

        async with self._pg_engine.begin() as conn:
            row = await conn.execute(
                select(UserProfile).where(
                    UserProfile.telegram_user_id == telegram_user_id
                )
            )
            p = row.scalar_one_or_none()
            if p is None:
                from sqlalchemy import insert

                await conn.execute(
                    insert(UserProfile).values(
                        telegram_user_id=telegram_user_id,
                        display_name=display_name,
                        address_as=address_as,
                        bio=bio,
                        preferences_json=preferences_json,
                    )
                )
            else:
                from sqlalchemy import update

                vals: dict[str, Any] = {}
                if display_name is not None:
                    vals["display_name"] = display_name
                if address_as is not None:
                    vals["address_as"] = address_as
                if bio is not None:
                    vals["bio"] = bio
                if preferences_json is not None:
                    vals["preferences_json"] = preferences_json
                if vals:
                    await conn.execute(
                        update(UserProfile)
                        .where(UserProfile.telegram_user_id == telegram_user_id)
                        .values(**vals)
                    )

    async def _get_active_project_pg(self, telegram_user_id: int) -> dict[str, Any] | None:
        from sqlalchemy import select

        from src.agents_tg.db.models import UserProject

        async with self._pg_engine.connect() as conn:
            rows = await conn.execute(
                select(UserProject)
                .where(
                    UserProject.telegram_user_id == telegram_user_id,
                    UserProject.status == "active",
                )
                .order_by(UserProject.updated_at.desc())
                .limit(1)
            )
            p = rows.scalar_one_or_none()
            if not p:
                return None
            return {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "status": p.status,
            }

    async def _set_active_project_pg(
        self,
        telegram_user_id: int,
        *,
        title: str,
        description: str | None,
    ) -> dict[str, Any]:
        from sqlalchemy import insert, update

        from src.agents_tg.db.models import UserProject

        async with self._pg_engine.begin() as conn:
            await conn.execute(
                update(UserProject)
                .where(
                    UserProject.telegram_user_id == telegram_user_id,
                    UserProject.status == "active",
                )
                .values(status="paused")
            )
            result = await conn.execute(
                insert(UserProject)
                .values(
                    telegram_user_id=telegram_user_id,
                    title=title,
                    description=description,
                    status="active",
                )
                .returning(UserProject.id)
            )
            pid = int(result.first()[0])
        return {
            "id": pid,
            "title": title,
            "description": description,
            "status": "active",
        }

    async def _update_project_status_pg(
        self,
        telegram_user_id: int,
        *,
        project_id: int | None,
        status: str,
    ) -> dict[str, Any]:
        from sqlalchemy import update

        from src.agents_tg.db.models import UserProject

        if project_id is None:
            active = await self._get_active_project_pg(telegram_user_id)
            if not active:
                return {"ok": False, "error": "project_not_found"}
            project_id = active["id"]

        async with self._pg_engine.begin() as conn:
            await conn.execute(
                update(UserProject)
                .where(
                    UserProject.id == project_id,
                    UserProject.telegram_user_id == telegram_user_id,
                )
                .values(status=status)
            )
        return {"ok": True, "id": project_id, "status": status}

    async def _log_activity_pg(
        self,
        telegram_user_id: int,
        *,
        project_id: int,
        agent_key: str,
        summary: str,
        kind: str,
    ) -> dict[str, Any]:
        from sqlalchemy import insert, update

        from src.agents_tg.db.models import ProjectActivity, UserProject

        async with self._pg_engine.begin() as conn:
            result = await conn.execute(
                insert(ProjectActivity)
                .values(
                    project_id=project_id,
                    telegram_user_id=telegram_user_id,
                    agent_key=agent_key,
                    kind=kind,
                    summary=summary,
                )
                .returning(ProjectActivity.id)
            )
            aid = int(result.first()[0])
            await conn.execute(
                update(UserProject)
                .where(UserProject.id == project_id)
                .values(updated_at=datetime.now(timezone.utc))
            )
        return {"ok": True, "id": aid, "project_id": project_id}

    async def _get_recent_activity_pg(
        self,
        telegram_user_id: int,
        *,
        project_id: int | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from src.agents_tg.db.models import ProjectActivity

        if project_id is None:
            project = await self._get_active_project_pg(telegram_user_id)
            if not project:
                return []
            project_id = project["id"]

        async with self._pg_engine.connect() as conn:
            rows = await conn.execute(
                select(ProjectActivity)
                .where(
                    ProjectActivity.telegram_user_id == telegram_user_id,
                    ProjectActivity.project_id == project_id,
                )
                .order_by(ProjectActivity.created_at.desc())
                .limit(limit)
            )
            return [
                {
                    "agent_key": a.agent_key,
                    "kind": a.kind,
                    "summary": a.summary,
                    "created_at": a.created_at.isoformat() if a.created_at else "",
                }
                for a in rows.scalars().all()
            ]


shared_context = SharedContextService()
