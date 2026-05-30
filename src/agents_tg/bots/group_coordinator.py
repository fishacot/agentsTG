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
        self._history: Dict[int, List[GroupMessage]] = {}
        self._group_members: Dict[int, set] = {}
        self._plans: Dict[int, List[str]] = {}
        self._last_agent_reply: Dict[int, str] = {}

    def register_group(self, chat_id: int, agent_keys: List[str]):
        """Register a group with its participating agents."""
        self._group_members[chat_id] = set(agent_keys)
        self._history[chat_id] = []
        logger.info(f"Registered group {chat_id} with agents: {agent_keys}")

    def set_plan(self, chat_id: int, plan: List[str]) -> None:
        self._plans[chat_id] = list(plan)

    def get_plan(self, chat_id: int) -> List[str]:
        return self._plans.get(chat_id, [])

    def format_plan(self, chat_id: int) -> str:
        plan = self.get_plan(chat_id)
        if not plan:
            return ""
        return "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))

    def should_skip_echo(self, chat_id: int, agent_key: str, text: str) -> bool:
        """Anti-echo: skip if same agent repeats prior reply without new info."""
        key = f"{chat_id}:{agent_key}"
        prev = self._last_agent_reply.get(key, "")
        if prev and text.strip() == prev.strip():
            return True
        self._last_agent_reply[key] = text
        return False

    def should_stay_silent(
        self, chat_id: int, user_text: str, agent_key: str = "orchestrator"
    ) -> bool:
        """NO_REPLY when user acknowledges after another agent already answered."""
        history = self._history.get(chat_id, [])
        if len(history) < 1:
            return False
        last = history[-1]
        if last.from_agent in ("user", agent_key):
            return False
        low = user_text.lower().strip()
        if len(low) > 40:
            return False
        ack = ("ок", "спасибо", "понял", "ясно", "хорошо", "да", "+", "👍", "🙏")
        return any(low == m or low.startswith(f"{m} ") for m in ack)

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
