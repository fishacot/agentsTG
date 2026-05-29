"""Telegram HTML formatting and safe message sending."""

from __future__ import annotations

import html
import logging
import re

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

logger = logging.getLogger(__name__)

_ALLOWED_TAGS = frozenset({"b", "i", "code", "pre", "a"})


def escape_html(text: str) -> str:
    return html.escape(text, quote=False)


def sanitize_html_for_telegram(text: str) -> str:
    """Keep allowed Telegram HTML tags; escape the rest."""
    if not text:
        return ""

    # Strip markdown code fences that break HTML mode
    cleaned = text.replace("```", "")
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"<code>\1</code>", cleaned)

    # If model already used HTML tags, trust whitelist only
    def replace_tag(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        if tag in _ALLOWED_TAGS:
            return match.group(0)
        return escape_html(match.group(0))

    cleaned = re.sub(r"</?(b|i|code|pre|a)(?:\s[^>]*)?>", replace_tag, cleaned, flags=re.I)

    # Balance: if no HTML tags at all, return as escaped plain
    if not re.search(r"<[a-z/]", cleaned, re.I):
        return escape_html(cleaned)

    return cleaned


async def send_agent_response(
    message: Message,
    text: str,
    *,
    reply_in_group: bool = False,
    thinking_message: Message | None = None,
) -> Message | None:
    """Send agent reply with HTML; fallback to plain text on parse errors."""
    safe = sanitize_html_for_telegram(text)

    async def _send(content: str, parse_mode: str | None) -> Message:
        kwargs: dict = {}
        if parse_mode:
            kwargs["parse_mode"] = parse_mode
        if reply_in_group:
            if thinking_message:
                await thinking_message.delete()
            return await message.reply(content, **kwargs)
        if thinking_message:
            return await thinking_message.edit_text(content, **kwargs)
        return await message.answer(content, **kwargs)

    try:
        return await _send(safe, "HTML")
    except TelegramBadRequest as exc:
        logger.warning("HTML parse failed, falling back to plain: %s", exc)
        plain = re.sub(r"<[^>]+>", "", text)
        try:
            return await _send(plain, None)
        except TelegramBadRequest:
            return await _send(plain[:4000], None)
