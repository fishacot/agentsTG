"""Group chat coordinator for inter-bot communication.

Tracks messages in shared group so bots can see what others said.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GroupMessage:
    """A message in the group chat."""

    message_id: int
    from_agent: str  # agent_key or "user"
    text: str
    timestamp: datetime
    mentions: List[str]  # list of mentioned agent usernames


class GroupCoordinator:
    """Coordinates communication in the shared group chat.

    - Tracks recent messages for context
    - Detects mentions of specific agents
    - Manages inter-bot awareness
    """

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self._history: Dict[int, List[GroupMessage]] = {}  # chat_id -> messages
        self._group_members: Dict[int, set] = {}  # chat_id -> set of agent_keys

    def register_group(self, chat_id: int, agent_keys: List[str]):
        """Register a group with its participating agents."""
        self._group_members[chat_id] = set(agent_keys)
        self._history[chat_id] = []
        logger.info(f"Registered group {chat_id} with agents: {agent_keys}")

    def add_message(self, chat_id: int, message: GroupMessage):
        """Add a message to group history."""
        if chat_id not in self._history:
            self._history[chat_id] = []

        self._history[chat_id].append(message)

        # Trim history if too long
        if len(self._history[chat_id]) > self.max_history:
            self._history[chat_id] = self._history[chat_id][-self.max_history :]

    def get_recent_context(self, chat_id: int, n_messages: int = 10) -> str:
        """Get recent conversation context as formatted text."""
        if chat_id not in self._history:
            return ""

        messages = self._history[chat_id][-n_messages:]
        lines = []

        for msg in messages:
            sender = f"@{msg.from_agent}" if msg.from_agent != "user" else "👤 User"
            lines.append(
                f"[{msg.timestamp.strftime('%H:%M')}] {sender}: {msg.text[:100]}"
            )

        return "\n".join(lines) if lines else "(No recent messages)"

    def get_mentions_for_agent(
        self, chat_id: int, agent_username: str
    ) -> List[GroupMessage]:
        """Get messages that mention a specific agent."""
        if chat_id not in self._history:
            return []

        agent_username_lower = agent_username.lower().replace("@", "")
        return [
            msg
            for msg in self._history[chat_id]
            if agent_username_lower in [m.lower() for m in msg.mentions]
        ]

    def is_agent_in_group(self, chat_id: int, agent_key: str) -> bool:
        """Check if an agent is part of this group."""
        return agent_key in self._group_members.get(chat_id, set())

    def get_colleagues_in_group(self, chat_id: int, exclude_agent: str) -> List[str]:
        """Get other agents in the same group."""
        members = self._group_members.get(chat_id, set())
        return [m for m in members if m != exclude_agent]


# Singleton
_group_coordinator: Optional[GroupCoordinator] = None


def get_coordinator() -> GroupCoordinator:
    """Get or create the group coordinator."""
    global _group_coordinator
    if _group_coordinator is None:
        _group_coordinator = GroupCoordinator()
    return _group_coordinator
