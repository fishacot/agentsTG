"""OpenClaw-style bootstrap blocks: TIME, USER, FOCUS, MEMORY, TOOLS."""

from __future__ import annotations

import logging
from pathlib import Path

from src.agents_tg.services.prompt_builder import PromptTier
from src.agents_tg.services.prompts.identity import human_name_for
from src.agents_tg.services.shared_context import shared_context
from src.agents_tg.utils.timezone_utils import now_local, now_local_display

logger = logging.getLogger(__name__)

_TOOLS_DIR = Path(__file__).resolve().parent.parent / "agents" / "tools"


def build_time_block() -> str:
    local = now_local()
    weekday = (
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    )[local.weekday()]
    return (
        f"\n\n## ВРЕМЯ\n"
        f"- Сейчас: {now_local_display()}\n"
        f"- День недели: {weekday}\n"
    )


async def build_user_block(
    telegram_user_id: int,
    *,
    tier: PromptTier,
    identity_facts: list[str] | None = None,
) -> str:
    if tier == PromptTier.LIGHT:
        profile = await shared_context.get_profile(telegram_user_id)
        name = profile.get("address_as") or profile.get("display_name")
        if name:
            return f"\n\n## ПОЛЬЗОВАТЕЛЬ\n- Обращайся: {name}\n"
        return ""

    profile = await shared_context.get_profile(telegram_user_id)
    if not profile and not identity_facts:
        return (
            "\n\n## ПОЛЬЗОВАТЕЛЬ\n"
            "- Профиль пока пуст. update_user_profile или remember_about_user "
            "— когда пользователь сообщит о себе.\n"
        )

    lines = ["\n\n## ПОЛЬЗОВАТЕЛЬ (общая память команды)"]
    if profile.get("display_name"):
        lines.append(f"- Имя: {profile['display_name']}")
    if profile.get("address_as"):
        lines.append(f"- Обращение: {profile['address_as']}")
    if profile.get("bio"):
        lines.append(f"- О себе: {profile['bio']}")
    prefs = profile.get("preferences") or {}
    if prefs.get("likes"):
        lines.append(f"- Нравится: {', '.join(prefs['likes'][:8])}")
    if prefs.get("dislikes"):
        lines.append(f"- Не нравится: {', '.join(prefs['dislikes'][:8])}")
    if prefs.get("style"):
        lines.append(f"- Стиль общения: {prefs['style']}")
    if identity_facts:
        lines.append("- Факты:")
        for f in identity_facts[:6]:
            lines.append(f"  • {f}")
    return "\n".join(lines)


async def build_focus_block(
    telegram_user_id: int,
    *,
    tier: PromptTier,
) -> str:
    if tier == PromptTier.LIGHT:
        return ""

    project = await shared_context.get_active_project(telegram_user_id)
    if not project:
        return ""

    activities = await shared_context.get_recent_activity(telegram_user_id, limit=5)
    lines = [
        "\n\n## ФОКУС (активный проект — видят все агенты)",
        f"- Проект: {project['title']}",
    ]
    if project.get("description"):
        lines.append(f"- Описание: {project['description'][:300]}")
    if activities:
        lines.append("- Недавняя работа коллег:")
        for a in activities:
            agent = human_name_for(a["agent_key"])
            lines.append(f"  • {agent}: {a['summary'][:120]}")
    return "\n".join(lines)


async def build_memory_curated_block(
    telegram_user_id: int,
    *,
    tier: PromptTier,
    all_facts: list[str],
) -> str:
    if tier == PromptTier.LIGHT:
        return ""
    if tier == PromptTier.STANDARD and len(all_facts) <= 3:
        return ""

    project = await shared_context.get_active_project(telegram_user_id)
    lines = ["\n\n## ПАМЯТЬ (сводка)"]
    if project:
        lines.append(f"- Активный проект: {project['title']}")
    if all_facts:
        lines.append("- Ключевые факты:")
        for f in all_facts[-10:]:
            lines.append(f"  • {f[:200]}")
    return "\n".join(lines)


def load_tools_md(agent_key: str, *, tier: PromptTier) -> str:
    if tier != PromptTier.FULL:
        return ""
    path = _TOOLS_DIR / f"{agent_key}.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    max_chars = 1500
    if len(text) > max_chars:
        text = text[:max_chars] + "\n… (см. agents/tools/)"
    return f"\n\n## TOOLS (заметки)\n{text}\n"


async def build_bootstrap_blocks(
    *,
    telegram_user_id: int,
    agent_key: str,
    tier: PromptTier,
    identity_facts: list[str] | None = None,
    all_facts: list[str] | None = None,
) -> dict[str, str]:
    """Assemble all OpenClaw bootstrap sections for one run."""
    return {
        "time_block": build_time_block(),
        "user_block": await build_user_block(
            telegram_user_id, tier=tier, identity_facts=identity_facts
        ),
        "focus_block": await build_focus_block(telegram_user_id, tier=tier),
        "memory_curated_block": await build_memory_curated_block(
            telegram_user_id,
            tier=tier,
            all_facts=all_facts or [],
        ),
        "tools_block": load_tools_md(agent_key, tier=tier),
    }
