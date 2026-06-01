"""Artifact delivery — sendDocument / file links to Telegram."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ArtifactService:
    """Register workspace artifacts and deliver via Telegram."""

    def __init__(self) -> None:
        self._registry: dict[str, Path] = {}

    def register(self, artifact_id: str, path: Path) -> None:
        self._registry[artifact_id] = path

    def get_path(self, artifact_id: str) -> Path | None:
        return self._registry.get(artifact_id)

    async def send_document(
        self,
        bot: Any,
        chat_id: int,
        path: Path,
        *,
        caption: str | None = None,
    ) -> bool:
        if not path.exists():
            logger.warning("Artifact not found: %s", path)
            return False
        try:
            from aiogram.types import FSInputFile

            doc = FSInputFile(str(path))
            await bot.send_document(chat_id=chat_id, document=doc, caption=caption)
            return True
        except Exception as exc:
            logger.error("sendDocument failed: %s", exc)
            return False

    async def deliver_artifact(
        self,
        bot: Any,
        chat_id: int,
        artifact_id: str,
        *,
        caption: str | None = None,
    ) -> bool:
        path = self.get_path(artifact_id)
        if not path:
            return False
        return await self.send_document(bot, chat_id, path, caption=caption)


artifact_service = ArtifactService()
