"""Telegram multi-bubble delivery with HTML-safe chunking."""

from __future__ import annotations

import html
import logging
import re

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

logger = logging.getLogger(__name__)

_ALLOWED_TAGS = frozenset({"b", "i", "code", "pre", "a"})
_PRE_OPEN = re.compile(r"<pre(?:\s[^>]*)?>", re.I)
_PRE_CLOSE = re.compile(r"</pre>", re.I)


def escape_html(text: str) -> str:
    return html.escape(text, quote=False)


def sanitize_html_for_telegram(text: str) -> str:
    """Keep allowed Telegram HTML tags; escape the rest."""
    if not text:
        return ""

    cleaned = text.replace("```", "")
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"<code>\1</code>", cleaned)

    def replace_tag(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        if tag in _ALLOWED_TAGS:
            return match.group(0)
        return escape_html(match.group(0))

    cleaned = re.sub(
        r"</?(b|i|code|pre|a)(?:\s[^>]*)?>", replace_tag, cleaned, flags=re.I
    )

    if not re.search(r"<[a-z/]", cleaned, re.I):
        return escape_html(cleaned)

    return cleaned


def _inside_pre(text: str, pos: int) -> bool:
    """Return True if pos is inside an unclosed <pre> block."""
    opens = len(_PRE_OPEN.findall(text[:pos]))
    closes = len(_PRE_CLOSE.findall(text[:pos]))
    return opens > closes


def _find_split_point(text: str, limit: int) -> int:
    """Prefer paragraph, newline, sentence, whitespace; never split inside <pre>."""
    if len(text) <= limit:
        return len(text)

    window = text[:limit]
    if _inside_pre(text, limit):
        # Walk back to before <pre> or force close at limit
        pre_start = window.rfind("<pre")
        if pre_start > limit // 2:
            return pre_start
        return limit

    for sep in ("\n\n", "\n", ". ", " "):
        idx = window.rfind(sep)
        if idx > limit // 3:
            return idx + len(sep)

    return limit


def split_telegram_html(text: str, limit: int = 4096) -> list[str]:
    """Split HTML text into Telegram-safe chunks."""
    if not text:
        return [""]

    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = _find_split_point(remaining, limit)
        if cut <= 0:
            cut = limit
        chunk = remaining[:cut].rstrip()
        # Close dangling <pre> if we cut mid-block
        if _inside_pre(chunk, len(chunk)) and not _PRE_CLOSE.search(chunk):
            chunk += "</pre>"
            remaining = "<pre>" + remaining[cut:].lstrip()
        else:
            remaining = remaining[cut:].lstrip()
        if chunk:
            chunks.append(chunk)

    return chunks or [""]


def _part_prefix(index: int, total: int) -> str:
    if total <= 1:
        return ""
    return f"<i>({index}/{total})</i>\n"


async def _send_one(
    message: Message,
    content: str,
    *,
    parse_mode: str | None,
    reply_in_group: bool,
    thinking_message: Message | None,
    use_thinking_edit: bool,
) -> Message:
    kwargs: dict = {}
    if parse_mode:
        kwargs["parse_mode"] = parse_mode

    if reply_in_group:
        if thinking_message and use_thinking_edit:
            await thinking_message.delete()
        return await message.reply(content, **kwargs)

    if thinking_message and use_thinking_edit:
        return await thinking_message.edit_text(content, **kwargs)
    return await message.answer(content, **kwargs)


async def _send_with_retry(
    message: Message,
    content: str,
    *,
    reply_in_group: bool,
    thinking_message: Message | None,
    use_thinking_edit: bool,
) -> Message | None:
    safe = sanitize_html_for_telegram(content)
    for attempt in range(2):
        try:
            return await _send_one(
                message,
                safe,
                parse_mode="HTML",
                reply_in_group=reply_in_group,
                thinking_message=thinking_message,
                use_thinking_edit=use_thinking_edit,
            )
        except TelegramBadRequest as exc:
            logger.warning("HTML send failed (attempt %s): %s", attempt + 1, exc)
            plain = re.sub(r"<[^>]+>", "", content)
            try:
                return await _send_one(
                    message,
                    plain,
                    parse_mode=None,
                    reply_in_group=reply_in_group,
                    thinking_message=thinking_message,
                    use_thinking_edit=use_thinking_edit,
                )
            except TelegramBadRequest:
                if attempt == 1:
                    raise
    return None


async def send_agent_response(
    message: Message,
    text: str,
    *,
    reply_in_group: bool = False,
    thinking_message: Message | None = None,
    chunk_limit: int = 4096,
) -> Message | None:
    """Send agent reply; split long text into numbered parts."""
    import asyncio
    import random

    from src.agents_tg.config.settings import get_settings

    settings = get_settings()
    parts = split_telegram_html(text, limit=chunk_limit)
    total = len(parts)
    last_sent: Message | None = None

    for i, part in enumerate(parts, start=1):
        if i > 1 and settings.HUMAN_DELAY_MS_MAX > 0:
            delay_ms = random.randint(
                settings.HUMAN_DELAY_MS_MIN, settings.HUMAN_DELAY_MS_MAX
            )
            await asyncio.sleep(delay_ms / 1000.0)
        body = _part_prefix(i, total) + part
        use_edit = i == 1 and thinking_message is not None
        try:
            last_sent = await _send_with_retry(
                message,
                body,
                reply_in_group=reply_in_group,
                thinking_message=thinking_message if use_edit else None,
                use_thinking_edit=use_edit,
            )
        except TelegramBadRequest as exc:
            logger.error("Failed to send part %s/%s: %s", i, total, exc)
            # Try smaller sub-chunks for this part only
            for sub in split_telegram_html(part, limit=chunk_limit // 2):
                sub_body = _part_prefix(i, total) + sub
                last_sent = await _send_with_retry(
                    message,
                    sub_body,
                    reply_in_group=reply_in_group,
                    thinking_message=None,
                    use_thinking_edit=False,
                )

    return last_sent
