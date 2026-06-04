"""Inbound message routing — debounce, mentions, gateway dispatch."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

if TYPE_CHECKING:
    from src.agents_tg.bots.agent_bot import AgentBot


def is_mentioned(message: Message, username: str) -> bool:
    """Check if this bot is mentioned in the message."""
    if not message.text:
        return False

    text_lower = message.text.lower()
    if f"@{username}" in text_lower:
        return True

    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention = message.text[
                    entity.offset : entity.offset + entity.length
                ].lower()
                if mention == f"@{username}":
                    return True

    return False


def extract_user_text(message: Message, username: str) -> str:
    """Remove bot mention from message text."""
    text = (message.text or "").strip()
    if not text:
        return ""

    pattern = re.compile(rf"@?{re.escape(username)}\b", re.IGNORECASE)
    cleaned = pattern.sub("", text).strip()
    return cleaned or text


def extract_mentions(text: str) -> list[str]:
    """Extract @username mentions from text."""
    return re.findall(r"@([A-Za-z0-9_]+)", text)


def is_research_intent(text: str) -> bool:
    low = text.lower()
    markers = (
        "найди",
        "поиск",
        "новост",
        "актуальн",
        "сравни",
        "research",
        "search",
    )
    return any(m in low for m in markers)


def register_inbound(router: Router, bot: AgentBot) -> None:
    """Register catch-all message handler for DM and group mentions."""

    @router.message()
    async def handle_message(message: Message, state: FSMContext):
        from src.agents_tg.config.settings import get_settings
        from src.agents_tg.services.inbound_turn import inbound_turn_service
        from src.agents_tg.services.message_pipeline import message_pipeline

        is_group = message.chat.type in ["group", "supergroup"]
        if is_group and not is_mentioned(message, bot.username):
            return

        # Dedupe only in gateway_router.dispatch (inbound_turn). Pre-check here
        # claimed the idempotency key and caused silent drops (~30ms, no "Думаю").

        settings = get_settings()
        message_pipeline.debounce_sec = settings.MESSAGE_DEBOUNCE_MS / 1000.0

        async def _run_handler(msg: Message, *, combined_text: str | None = None):
            await inbound_turn_service.handle(
                bot,
                msg,
                state,
                combined_text=combined_text,
            )

        if settings.MESSAGE_DEBOUNCE_MS > 0 and not is_group:
            await message_pipeline.enqueue_debounced(
                agent_key=bot.agent_key,
                message=message,
                handler=_run_handler,
            )
        elif message_pipeline.is_busy(bot.agent_key, message.chat.id):
            message_pipeline.queue_followup(
                agent_key=bot.agent_key,
                message=message,
                handler=_run_handler,
            )
        else:
            await _run_handler(message)
