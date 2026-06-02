"""Memory and scheduled-context blocks for system prompts."""

from __future__ import annotations

import re

from src.agents_tg.services.prompts.tier_rules import PromptTier


async def build_memory_block(
    user_message: str,
    user_id: str,
    tier: PromptTier,
    memory_search_fn,
) -> str:
    if tier == PromptTier.LIGHT:
        if not re.search(r"(?i)помни|памят|запомин", user_message):
            return ""
    limit = 3 if tier == PromptTier.LIGHT else 6 if tier == PromptTier.STANDARD else 8
    memories = await memory_search_fn(user_message, user_id=user_id, limit=limit)
    if not memories:
        if tier == PromptTier.LIGHT:
            return ""
        return (
            "\n\nПАМЯТЬ: пока нет фактов. remember_about_user — "
            "когда пользователь сообщает факт о себе.\n"
        )
    lines = []
    for item in memories:
        text = item.get("text") or item.get("memory") or ""
        if text:
            lines.append(f"- {text}")
    if not lines:
        return ""
    return "\n\nПАМЯТЬ:\n" + "\n".join(lines)


def build_scheduled_context(lines: list[str]) -> str:
    """Inject proactive scheduler facts into output_hints."""
    if not lines:
        return ""
    return (
        "\n\n## Уже выполнено планировщиком (факт)\n"
        + "\n".join(lines)
        + "\nПодтверди пользователю, что автономная доставка настроена. "
        "Не говори, что не можешь писать сама — сервер уже запланировал отправку."
    )
