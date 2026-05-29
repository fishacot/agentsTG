"""Memory service using Mem0 for long-term user context."""

import logging
from typing import Any, Dict, List, Optional

try:
    from mem0 import Memory
except ImportError:  # pragma: no cover - optional in minimal envs
    Memory = None  # type: ignore[misc, assignment]

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryService:
    """Service to manage long-term memory for users."""

    def __init__(self) -> None:
        config = {}
        if settings.MEM0_API_KEY:
            config["api_key"] = settings.MEM0_API_KEY

        try:
            if Memory is not None:
                self.memory = Memory.from_config(config)
            else:
                self.memory = None
        except Exception as e:
            logger.error("Failed to initialize Mem0: %s. Using fallback memory.", e)
            self.memory = None

        # Fallback: in-process facts per user when Mem0/cloud unavailable.
        self._journal_store: Dict[str, list[dict[str, Any]]] = {}
        self._facts_store: Dict[str, list[str]] = {}

    async def add(
        self, data: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add information to user memory."""
        text = data.strip()
        if not text:
            return

        self._facts_store.setdefault(user_id, [])
        if text not in self._facts_store[user_id]:
            self._facts_store[user_id].append(text)
            if len(self._facts_store[user_id]) > 100:
                self._facts_store[user_id] = self._facts_store[user_id][-100:]

        if self.memory:
            try:
                self.memory.add(text, user_id=user_id, metadata=metadata or {})
            except Exception as e:
                logger.error("Error adding to memory: %s", e)

        await self.add_journal_entry(
            user_id=user_id,
            agent=metadata.get("agent") if metadata else None,
            event="memory_add",
            payload={"text": text},
        )

    async def search(
        self, query: str, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search in user memory (Mem0 or local fallback)."""
        if self.memory:
            try:
                results = self.memory.search(query, user_id=user_id, limit=limit)
                if results:
                    return results
            except Exception as e:
                logger.error("Error searching memory: %s", e)

        return self._fallback_search(query, user_id, limit)

    def _fallback_search(
        self, query: str, user_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        facts = self._facts_store.get(user_id, [])
        if not facts:
            return []

        q = query.lower().strip()
        if not q or len(q) < 3:
            selected = facts[-limit:]
        else:
            matched = [f for f in facts if q in f.lower()]
            selected = matched[-limit:] if matched else facts[-limit:]

        return [{"text": fact} for fact in selected]

    async def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all memories for a user."""
        if self.memory:
            try:
                return self.memory.get_all(user_id=user_id)
            except Exception as e:
                logger.error("Error getting all memories: %s", e)

        return [{"text": f} for f in self._facts_store.get(user_id, [])]

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


memory_service = MemoryService()
