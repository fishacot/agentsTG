"""Confirmation gates with PG persistence + Telegram inline UX."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncEngine

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)

GATED_ACTIONS = frozenset(
    {
        "update_project_status:done",
        "deploy_hook",
        "delete_data",
        "run_code",
    }
)


@dataclass
class PendingConfirmation:
    token: str
    telegram_user_id: int
    action: str
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConfirmationService:
    """PG-backed pending confirmations with in-memory fallback."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}
        self._engine: AsyncEngine | None = None

    def set_pg_engine(self, engine: AsyncEngine | None) -> None:
        self._engine = engine

    def requires_confirmation(self, action: str) -> bool:
        if not get_settings().REQUIRE_CONFIRM:
            return False
        return action in GATED_ACTIONS

    def _is_expired(self, entry: PendingConfirmation) -> bool:
        ttl = int(get_settings().CONFIRMATION_TTL_SEC)
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        return age > ttl

    def register(
        self,
        *,
        telegram_user_id: int,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> PendingConfirmation:
        token = uuid.uuid4().hex[:12]
        entry = PendingConfirmation(
            token=token,
            telegram_user_id=telegram_user_id,
            action=action,
            payload=payload or {},
        )
        self._pending[token] = entry
        logger.info(
            "Confirmation registered action=%s user=%s token=%s",
            action,
            telegram_user_id,
            token,
        )
        return entry

    async def register_and_persist(
        self,
        *,
        telegram_user_id: int,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> PendingConfirmation:
        entry = self.register(
            telegram_user_id=telegram_user_id,
            action=action,
            payload=payload,
        )
        await self.persist_register(entry)
        return entry

    async def persist_register(self, entry: PendingConfirmation) -> None:
        if not self._engine:
            return
        try:
            from src.agents_tg.db.models import PendingConfirmation as PC

            async with self._engine.begin() as conn:
                await conn.execute(
                    insert(PC).values(
                        token=entry.token,
                        telegram_user_id=entry.telegram_user_id,
                        action=entry.action,
                        payload=entry.payload,
                    )
                )
        except Exception as exc:
            logger.warning("PG confirmation persist failed: %s", exc)

    def get(self, token: str) -> PendingConfirmation | None:
        entry = self._pending.get(token)
        if entry and self._is_expired(entry):
            self._pending.pop(token, None)
            return None
        return entry

    def consume(self, token: str) -> PendingConfirmation | None:
        entry = self._pending.pop(token, None)
        if entry and self._is_expired(entry):
            return None
        return entry

    async def persist_consume(self, token: str) -> None:
        if not self._engine:
            return
        try:
            from src.agents_tg.db.models import PendingConfirmation as PC

            async with self._engine.begin() as conn:
                await conn.execute(
                    update(PC).where(PC.token == token).values(status="consumed")
                )
        except Exception as exc:
            logger.warning("PG confirmation consume failed: %s", exc)

    def hint_for_action(self, action: str) -> str:
        return (
            f"Действие «{action}» требует явного подтверждения. "
            "Нажмите «Да» или «Нет»."
        )

    def inline_keyboard(self, token: str) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "✅ Да", "callback_data": f"confirm:{token}:yes"},
                    {"text": "❌ Нет", "callback_data": f"confirm:{token}:no"},
                ]
            ]
        }


confirmation_service = ConfirmationService()
