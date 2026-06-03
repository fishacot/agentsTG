"""Owner playbook (RULES.md) injection into prompts."""

from __future__ import annotations

from pathlib import Path

from src.agents_tg.config.settings import get_settings

_MAX_CHARS = 2500


def playbook_path(user_id: str) -> Path:
    settings = get_settings()
    root = settings.ROOT_DIR / "workspace" / "users" / str(user_id)
    return root / "RULES.md"


def load_playbook_block(user_id: str) -> str:
    path = playbook_path(user_id)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not text:
        return ""
    clipped = text[:_MAX_CHARS]
    return f"## Правила владельца (playbook)\n{clipped}"
