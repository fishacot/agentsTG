"""Single-message plan progress (Manus-style editMessage)."""

from __future__ import annotations

import logging
from typing import Any

from src.agents_tg.services.progress_ux import cancel_keyboard

logger = logging.getLogger(__name__)


class PlanProgressTracker:
    """One Telegram status message, updated via editMessageText."""

    def __init__(self, message: Any, *, task_id: str) -> None:
        self._message = message
        self._task_id = task_id
        self._status_msg: Any | None = None

    async def update(self, body_html: str, *, show_cancel: bool = False) -> None:
        from src.agents_tg.utils.telegram_format import sanitize_html_for_telegram

        text = sanitize_html_for_telegram(body_html)
        markup = cancel_keyboard(self._task_id) if show_cancel else None
        if self._status_msg is None:
            self._status_msg = await self._message.answer(
                text,
                parse_mode="HTML",
                reply_markup=markup,
            )
            return
        try:
            await self._status_msg.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception as exc:
            logger.debug("Plan progress edit failed, re-send: %s", exc)
            self._status_msg = await self._message.answer(
                text,
                parse_mode="HTML",
                reply_markup=markup,
            )
