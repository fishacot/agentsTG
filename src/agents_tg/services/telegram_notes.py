"""Post notes to a Telegram channel via the PA bot."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from src.agents_tg.config.settings import get_settings
from src.agents_tg.utils.telegram_format import escape_html, sanitize_html_for_telegram

logger = logging.getLogger(__name__)


async def post_to_notes_channel(title: str, body: str) -> dict:
    """Publish a note to NOTES_CHANNEL_ID using BOT_TOKEN_PA."""
    settings = get_settings()
    channel_id = settings.NOTES_CHANNEL_ID
    token = settings.BOT_TOKEN_PA

    if not channel_id:
        return {"ok": False, "error": "notes_channel_not_configured"}
    if not token:
        return {"ok": False, "error": "pa_bot_token_missing"}

    safe_title = escape_html(title.strip())
    safe_body = sanitize_html_for_telegram(body.strip())
    text = f"<b>{safe_title}</b>\n\n{safe_body}"

    bot = Bot(token=token, default=DefaultBotProperties())
    try:
        msg = await bot.send_message(
            chat_id=channel_id, text=text[:4096], parse_mode="HTML"
        )
        return {
            "ok": True,
            "channel_id": channel_id,
            "message_id": msg.message_id,
        }
    except Exception as exc:
        logger.exception("Failed to post to notes channel")
        return {"ok": False, "error": str(exc)}
    finally:
        await bot.session.close()
