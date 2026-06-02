"""Live preview via Telegram editMessageText (pseudo-streaming)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

from src.agents_tg.channels.telegram_delivery import sanitize_html_for_telegram

if TYPE_CHECKING:
    from aiogram.types import Message

logger = logging.getLogger(__name__)

_CURSOR = " ▌"
_MIN_EDIT_INTERVAL_MS = 280
_TELEGRAM_TEXT_LIMIT = 4096


class PreviewStreamer:
    """Update a placeholder message as outbound text grows (throttled edits)."""

    def __init__(
        self,
        message: Message,
        *,
        min_edit_interval_ms: int = _MIN_EDIT_INTERVAL_MS,
        show_cursor: bool = True,
    ) -> None:
        self._message = message
        self._min_edit_interval_ms = min_edit_interval_ms
        self._show_cursor = show_cursor
        self._last_edit_ms: float = 0.0
        self._last_shown = ""

    async def update(self, text: str, *, force: bool = False) -> None:
        body = (text or "").strip()
        if not body:
            return

        display = body[: _TELEGRAM_TEXT_LIMIT - len(_CURSOR)]
        if self._show_cursor and len(body) < _TELEGRAM_TEXT_LIMIT:
            display = display + _CURSOR

        if display == self._last_shown and not force:
            return

        now_ms = time.monotonic() * 1000.0
        if (
            not force
            and self._last_edit_ms
            and now_ms - self._last_edit_ms < self._min_edit_interval_ms
        ):
            return

        safe = sanitize_html_for_telegram(display)
        try:
            await self._message.edit_text(safe, parse_mode="HTML")
            self._last_shown = display
            self._last_edit_ms = now_ms
        except TelegramBadRequest as exc:
            logger.debug("preview edit skipped: %s", exc)

    async def finalize(self, text: str) -> None:
        """Last preview update without streaming cursor."""
        body = (text or "").strip()
        if not body:
            return
        display = body[:_TELEGRAM_TEXT_LIMIT]
        if display == self._last_shown:
            return
        safe = sanitize_html_for_telegram(display)
        try:
            await self._message.edit_text(safe, parse_mode="HTML")
            self._last_shown = display
        except TelegramBadRequest as exc:
            logger.debug("preview finalize skipped: %s", exc)
