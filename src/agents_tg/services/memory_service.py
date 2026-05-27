"""Memory service using Mem0 for long-term user context."""

import logging
from typing import Any, Dict, List, Optional

from mem0 import Memory

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryService:
    """Service to manage long-term memory for users."""

    def __init__(self) -> None:
        # If MEM0_API_KEY is provided, it uses the managed cloud service
        # Otherwise, it can work with local vector stores (qdrant/chroma)
        config = {}
        if settings.MEM0_API_KEY:
            config["api_key"] = settings.MEM0_API_KEY

        try:
            self.memory = Memory.from_config(config)
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}. Using fallback memory.")
            self.memory = None

        # Simple in-process fallback journal, если Mem0 недоступен.
        self._journal_store: Dict[str, list[dict[str, Any]]] = {}

    async def add(
        self, data: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add information to user memory."""
        if self.memory:
            try:
                self.memory.add(data, user_id=user_id, metadata=metadata or {})
            except Exception as e:
                logger.error(f"Error adding to memory: {e}")

        # Журналируем факт даже без Mem0.
        await self.add_journal_entry(
            user_id=user_id,
            agent=metadata.get("agent") if metadata else None,
            event="memory_add",
            payload={"text": data},
        )

    async def search(
        self, query: str, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search in user memory."""
        if not self.memory:
            return []

        try:
            return self.memory.search(query, user_id=user_id, limit=limit)
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []

    async def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all memories for a user."""
        if not self.memory:
            return []

        try:
            return self.memory.get_all(user_id=user_id)
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            return []

    async def add_journal_entry(
        self,
        user_id: str,
        agent: Optional[str],
        event: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append structured journal entry for an agent (Manus-style log)."""
        key = f"{user_id}:{agent or 'orchestrator'}"
        entry = {
            "event": event,
            "payload": payload or {},
        }
        self._journal_store.setdefault(key, []).append(entry)

    async def get_journal(
        self, user_id: str, agent: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Return in-process journal entries for a user/agent."""
        key = f"{user_id}:{agent or 'orchestrator'}"
        return list(self._journal_store.get(key, []))


# Singleton instance
memory_service = MemoryService()
