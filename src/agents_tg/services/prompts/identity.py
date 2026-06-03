"""Soul loading and agent identity for prompt assembly."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.agents_tg.services.agent_identity import get_agent_identity

logger = logging.getLogger(__name__)

_SOULS_DIR = Path(__file__).resolve().parent.parent.parent / "agents" / "souls"

# Legacy soul filenames that differ from agent_key
_SOUL_FILE_ALIASES: dict[str, str] = {
    "coder": "coder_soul.md",
    "general": "general.md",
    "research": "research.md",
    "sports_analyst": "research.md",
}


def souls_dir() -> Path:
    return _SOULS_DIR


def soul_path_for(agent_key: str, *, soul_file: str | None = None) -> Path:
    if soul_file:
        return _SOULS_DIR / soul_file
    alias = _SOUL_FILE_ALIASES.get(agent_key)
    if alias:
        return _SOULS_DIR / alias
    return _SOULS_DIR / f"{agent_key}.md"


def load_soul(agent_key: str, *, soul_file: str | None = None) -> str:
    """Load SOUL markdown for an agent."""
    path = soul_path_for(agent_key, soul_file=soul_file)
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning("SOUL file for %s not found at %s.", agent_key, path)
    return ""


def resolve_identity(agent_key: str) -> dict[str, Any]:
    """Return agent identity dict (human name, designation, etc.)."""
    return get_agent_identity(agent_key)


def human_name_for(agent_key: str) -> str:
    """Short human name for bootstrap/focus blocks."""
    identity = get_agent_identity(agent_key)
    return str(identity.get("human_name") or agent_key)


def prompt_identity(agent_key: str) -> tuple[str, str]:
    """Return (human_name, designation) for system prompt header."""
    identity = get_agent_identity(agent_key)
    human_name = str(identity.get("human_name") or agent_key)
    designation = str(identity.get("designation") or "")
    return human_name, designation
