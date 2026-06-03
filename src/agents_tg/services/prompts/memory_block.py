"""Memory and scheduled-context blocks for system prompts."""

from __future__ import annotations

import re

from src.agents_tg.services.notebook import load_notebook_block
from src.agents_tg.services.prompts.tier_rules import PromptTier


def _task_session_suffix(task_id: str | None) -> str:
    if not task_id:
        return ""
    return (
        f"\n\nСЕССИЯ ЗАДАЧИ: {task_id} — не смешивай с другими несвязанными темами.\n"
    )


async def build_memory_block(
    user_message: str,
    user_id: str,
    tier: PromptTier,
    memory_search_fn,
    *,
    task_id: str | None = None,
) -> str:
    session = _task_session_suffix(task_id)
    notebook = load_notebook_block(user_id) if tier != PromptTier.LIGHT else ""
    if tier == PromptTier.LIGHT:
        if not re.search(r"(?i)помни|памят|запомин", user_message):
            return notebook + session
    limit = 3 if tier == PromptTier.LIGHT else 6 if tier == PromptTier.STANDARD else 8
    memories = await memory_search_fn(user_message, user_id=user_id, limit=limit)
    if not memories:
        if tier == PromptTier.LIGHT:
            return notebook + session
        return (
            notebook + "\n\nПАМЯТЬ: пока нет фактов. remember_about_user — "
            "когда пользователь сообщает факт о себе.\n"
        ) + session
    lines = []
    for item in memories:
        text = item.get("text") or item.get("memory") or ""
        if text:
            lines.append(f"- {text}")
    if not lines:
        return notebook + session
    return notebook + "\n\nПАМЯТЬ:\n" + "\n".join(lines) + session


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
