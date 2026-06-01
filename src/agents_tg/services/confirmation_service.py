"""Confirmation gates for destructive or high-impact actions (Manus-style)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)

GATED_ACTIONS = frozenset(
    {
        "update_project_status:done",
        "deploy_hook",
        "delete_data",
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
    """In-memory pending confirmations; cleared on restart."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}

    def requires_confirmation(self, action: str) -> bool:
        if not get_settings().REQUIRE_CONFIRM:
            return False
        return action in GATED_ACTIONS

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

    def get(self, token: str) -> PendingConfirmation | None:
        return self._pending.get(token)

    def consume(self, token: str) -> PendingConfirmation | None:
        return self._pending.pop(token, None)

    def hint_for_action(self, action: str) -> str:
        return (
            f"Действие «{action}» требует явного подтверждения. "
            "Спроси пользователя «Подтверждаете?» и только после «да» выполняй."
        )


confirmation_service = ConfirmationService()
