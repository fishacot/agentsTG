"""Session manager: (user_id, agent_key) → session_id."""

from __future__ import annotations

from src.agents_tg.gateway.envelope import new_session_id


class SessionManager:
    """In-process session map; PG persistence optional later."""

    def __init__(self) -> None:
        self._sessions: dict[str, str] = {}

    def _key(self, user_id: int, agent_key: str) -> str:
        return f"{user_id}:{agent_key}"

    def get_or_create(self, user_id: int, agent_key: str) -> str:
        key = self._key(user_id, agent_key)
        if key not in self._sessions:
            self._sessions[key] = new_session_id(user_id, agent_key)
        return self._sessions[key]

    def get(self, user_id: int, agent_key: str) -> str | None:
        return self._sessions.get(self._key(user_id, agent_key))

    def reset(self, user_id: int, agent_key: str) -> str:
        sid = new_session_id(user_id, agent_key)
        self._sessions[self._key(user_id, agent_key)] = sid
        return sid


session_manager = SessionManager()
