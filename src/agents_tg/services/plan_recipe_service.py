"""Persist successful plan templates for orchestrator reuse."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def intent_hash(text: str) -> str:
    normalized = " ".join((text or "").lower().split())[:400]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:64]


@dataclass
class PlanRecipeView:
    id: int
    user_id: int
    intent_hash: str
    intent_sample: str
    steps_json: list[Any]
    success_count: int


class PlanRecipeService:
    """Save/list plan recipes (PG with in-memory fallback)."""

    def __init__(self) -> None:
        self._pg_engine: Any | None = None
        self._memory: dict[int, list[PlanRecipeView]] = {}
        self._next_id = 1

    def set_pg_engine(self, engine: Any) -> None:
        self._pg_engine = engine

    async def save_recipe(
        self,
        *,
        user_id: int,
        intent_sample: str,
        steps_json: list[Any],
    ) -> PlanRecipeView | None:
        if not steps_json:
            return None
        sample = (intent_sample or "").strip()[:512]
        if not sample:
            return None
        ih = intent_hash(sample)

        if self._pg_engine:
            try:
                return await self._save_pg(
                    user_id=user_id,
                    intent_hash=ih,
                    intent_sample=sample,
                    steps_json=steps_json,
                )
            except Exception as exc:
                logger.debug("PG plan recipe save failed: %s", exc)

        bucket = self._memory.setdefault(user_id, [])
        for row in bucket:
            if row.intent_hash == ih:
                row.success_count += 1
                row.steps_json = steps_json
                return row
        rid = self._next_id
        self._next_id += 1
        view = PlanRecipeView(
            id=rid,
            user_id=user_id,
            intent_hash=ih,
            intent_sample=sample,
            steps_json=steps_json,
            success_count=1,
        )
        bucket.append(view)
        return view

    async def _save_pg(
        self,
        *,
        user_id: int,
        intent_hash: str,
        intent_sample: str,
        steps_json: list[Any],
    ) -> PlanRecipeView | None:
        from sqlalchemy import select, update
        from sqlalchemy.dialects.postgresql import insert

        from src.agents_tg.db.models import PlanRecipe

        async with self._pg_engine.begin() as conn:
            existing = await conn.execute(
                select(PlanRecipe).where(
                    PlanRecipe.user_id == user_id,
                    PlanRecipe.intent_hash == intent_hash,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                new_count = int(row.success_count or 0) + 1
                await conn.execute(
                    update(PlanRecipe)
                    .where(PlanRecipe.id == row.id)
                    .values(
                        steps_json=steps_json,
                        success_count=new_count,
                        intent_sample=intent_sample,
                    )
                )
                return PlanRecipeView(
                    id=row.id,
                    user_id=user_id,
                    intent_hash=intent_hash,
                    intent_sample=intent_sample,
                    steps_json=steps_json,
                    success_count=new_count,
                )

            stmt = (
                insert(PlanRecipe)
                .values(
                    user_id=user_id,
                    intent_hash=intent_hash,
                    intent_sample=intent_sample,
                    steps_json=steps_json,
                    success_count=1,
                )
                .returning(PlanRecipe)
            )
            result = await conn.execute(stmt)
            inserted = result.scalar_one()
            return PlanRecipeView(
                id=inserted.id,
                user_id=user_id,
                intent_hash=intent_hash,
                intent_sample=intent_sample,
                steps_json=steps_json,
                success_count=1,
            )

    async def list_recipes(
        self,
        *,
        user_id: int,
        limit: int = 10,
    ) -> list[PlanRecipeView]:
        limit = max(1, min(limit, 50))
        if self._pg_engine:
            try:
                from sqlalchemy import select

                from src.agents_tg.db.models import PlanRecipe

                async with self._pg_engine.connect() as conn:
                    result = await conn.execute(
                        select(PlanRecipe)
                        .where(PlanRecipe.user_id == user_id)
                        .order_by(PlanRecipe.success_count.desc())
                        .limit(limit)
                    )
                    rows = result.scalars().all()
                    return [
                        PlanRecipeView(
                            id=r.id,
                            user_id=r.user_id,
                            intent_hash=r.intent_hash,
                            intent_sample=r.intent_sample,
                            steps_json=list(r.steps_json or []),
                            success_count=r.success_count,
                        )
                        for r in rows
                    ]
            except Exception as exc:
                logger.debug("PG plan recipe list failed: %s", exc)

        bucket = self._memory.get(user_id, [])
        return sorted(bucket, key=lambda r: r.success_count, reverse=True)[:limit]

    async def find_by_intent(
        self,
        *,
        user_id: int,
        intent_sample: str,
    ) -> PlanRecipeView | None:
        ih = intent_hash(intent_sample)
        recipes = await self.list_recipes(user_id=user_id, limit=100)
        for r in recipes:
            if r.intent_hash == ih:
                return r
        return None


plan_recipe_service = PlanRecipeService()
