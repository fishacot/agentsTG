"""Telegram channel adapter: aiogram Message → OpenClawEnvelope."""

from __future__ import annotations

from aiogram.types import Message

from src.agents_tg.gateway.envelope import MediaItem, OpenClawEnvelope


def from_update(message: Message, agent_key: str) -> OpenClawEnvelope:
    """Convert aiogram Message to OpenClawEnvelope."""
    user_id = message.from_user.id if message.from_user else 0
    is_group = message.chat.type in ("group", "supergroup")
    text = (message.text or message.caption or "").strip()
    media: list[MediaItem] = []

    if message.photo:
        media.append(
            MediaItem(
                kind="photo",
                file_id=message.photo[-1].file_id,
                caption=message.caption,
                placeholder="[фото]",
            )
        )
    if message.voice:
        media.append(
            MediaItem(
                kind="voice",
                mime_type=message.voice.mime_type,
                file_id=message.voice.file_id,
                placeholder="[голосовое сообщение]",
            )
        )
    if message.document:
        media.append(
            MediaItem(
                kind="document",
                mime_type=message.document.mime_type,
                file_id=message.document.file_id,
                caption=message.caption,
                placeholder=f"[документ: {message.document.file_name or 'file'}]",
            )
        )

    metadata: dict = {
        "username": message.from_user.username if message.from_user else None,
        "chat_type": message.chat.type,
    }

    return OpenClawEnvelope(
        channel="telegram",
        chat_id=message.chat.id,
        user_id=user_id,
        text=text,
        media=media,
        message_id=message.message_id,
        agent_key=agent_key,
        is_group=is_group,
        metadata=metadata,
    )
