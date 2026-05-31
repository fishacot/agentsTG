"""Workspace file mirror: USER.md, MEMORY.md, daily logs (OpenClaw parity)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from src.agents_tg.config.settings import get_settings
from src.agents_tg.utils.timezone_utils import now_local

logger = logging.getLogger(__name__)


def _workspace_root(telegram_user_id: int) -> Path:
    settings = get_settings()
    root = settings.ROOT_DIR / "workspace" / "users" / str(telegram_user_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(exist_ok=True)
    return root


def write_user_md(
    telegram_user_id: int,
    *,
    display_name: str | None = None,
    address_as: str | None = None,
    bio: str | None = None,
    preferences: dict | None = None,
) -> None:
    root = _workspace_root(telegram_user_id)
    path = root / "USER.md"
    lines = ["# USER — профиль владельца", ""]
    if display_name:
        lines.append(f"- **Имя:** {display_name}")
    if address_as:
        lines.append(f"- **Обращение:** {address_as}")
    if bio:
        lines.append(f"- **О себе:** {bio}")
    prefs = preferences or {}
    if prefs.get("likes"):
        lines.append(f"- **Нравится:** {', '.join(prefs['likes'])}")
    if prefs.get("dislikes"):
        lines.append(f"- **Не нравится:** {', '.join(prefs['dislikes'])}")
    if prefs.get("style"):
        lines.append(f"- **Стиль:** {prefs['style']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_daily_log(
    telegram_user_id: int,
    *,
    agent_key: str,
    text: str,
) -> None:
    root = _workspace_root(telegram_user_id)
    day = now_local().strftime("%Y-%m-%d")
    path = root / "memory" / f"{day}.md"
    stamp = now_local().strftime("%H:%M")
    line = f"- [{stamp}] **{agent_key}:** {text[:400]}\n"
    if path.exists():
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    else:
        path.write_text(f"# {day}\n\n{line}", encoding="utf-8")


def refresh_memory_md(
    telegram_user_id: int,
    *,
    project_title: str | None = None,
    facts: list[str] | None = None,
) -> None:
    root = _workspace_root(telegram_user_id)
    path = root / "MEMORY.md"
    lines = ["# MEMORY — сводка", ""]
    if project_title:
        lines.append(f"- **Активный проект:** {project_title}")
    if facts:
        lines.append("- **Факты:**")
        for f in facts[-10:]:
            lines.append(f"  - {f[:200]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_heartbeat_md(telegram_user_id: int) -> str:
    """Load per-user HEARTBEAT checklist or repo default."""
    settings = get_settings()
    user_path = (
        settings.ROOT_DIR / "workspace" / "users" / str(telegram_user_id) / "HEARTBEAT.md"
    )
    default_path = settings.ROOT_DIR / "workspace" / "HEARTBEAT.default.md"
    if user_path.exists():
        return user_path.read_text(encoding="utf-8").strip()
    if default_path.exists():
        return default_path.read_text(encoding="utf-8").strip()
    return (
        "- Открытые задачи?\n"
        "- Активный проект?\n"
        "Если нечего сказать — ответь HEARTBEAT_OK."
    )
