"""OpenClaw L1 envelope — channel-agnostic inbound message."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class MediaItem(BaseModel):
    """Normalized media attachment (voice/photo/document stub)."""

    kind: str = "text"
    mime_type: str | None = None
    file_id: str | None = None
    caption: str | None = None
    placeholder: str | None = None


class OpenClawEnvelope(BaseModel):
    """Typed inbound message for gateway dispatch."""

    channel: str = "telegram"
    chat_id: int
    user_id: int
    text: str = ""
    media: list[MediaItem] = Field(default_factory=list)
    message_id: int
    agent_key: str
    is_group: bool = False
    idempotency_key: str = ""
    session_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def fill_idempotency(self) -> OpenClawEnvelope:
        if not self.idempotency_key:
            self.idempotency_key = f"{self.agent_key}:{self.chat_id}:{self.message_id}"
        return self

    @property
    def combined_text(self) -> str:
        parts = [self.text.strip()] if self.text.strip() else []
        for item in self.media:
            if item.placeholder:
                parts.append(item.placeholder)
            elif item.caption:
                parts.append(item.caption)
        return "\n".join(parts).strip()

    def with_session(self, session_id: str) -> OpenClawEnvelope:
        return self.model_copy(update={"session_id": session_id})

    def to_job_payload(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "text": self.text,
            "message_id": self.message_id,
            "is_group": self.is_group,
            "idempotency_key": self.idempotency_key,
            "metadata": self.metadata,
        }


def new_session_id(user_id: int, agent_key: str) -> str:
    return f"{user_id}:{agent_key}:{uuid4().hex[:8]}"
