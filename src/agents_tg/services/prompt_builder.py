"""Tiered system prompts to reduce LLM token usage."""

from __future__ import annotations

import re
from enum import Enum

from src.agents_tg.services.agent_prompts import (
    GOAL_DIRECTIVE,
    TELEGRAM_AGENT_PROTOCOL,
    TELEGRAM_HTML_FORMAT,
    WEB_TOOL_HINT,
)
from src.agents_tg.services.environment_context import AgentEnvironment

# Greetings, meta-questions — minimal prompt, no tools
_LIGHT_GREETING = re.compile(
    r"^(?:"
    r"привет|здравств|добрый|hi|hello|hey"
    r"|как дела|как ты|что нового"
    r"|кто ты|ты кто|представься"
    r"|ты помнишь|можешь запоминать|помнишь меня"
    r"|спасибо|thanks|thank you"
    r")[\s!?.,]*$",
    re.IGNORECASE,
)
_LIGHT_CAPABILITIES = re.compile(
    r"(?:расскажи|опиши|покажи).{0,30}(?:"
    r"что ты можешь|чем можешь|твои возможности|умеешь"
    r")",
    re.IGNORECASE,
)

# Explicit actions — full tools + soul
_ACTION_PATTERN = re.compile(
    r"(?i)("
    r"создай|создать|запиши|записать|сохрани|сохранить"
    r"|найди|найти|поиск|исследуй|research"
    r"|добавь задач|список дел|list tasks"
    r"|запомни что|remember"
    r"|deep_research|заметк"
    r")"
)


class PromptTier(str, Enum):
    LIGHT = "light"
    STANDARD = "standard"
    FULL = "full"


def detect_prompt_tier(user_message: str, *, include_web_tools: bool = False) -> PromptTier:
    text = (user_message or "").strip()
    if not text:
        return PromptTier.LIGHT
    if _ACTION_PATTERN.search(text):
        return PromptTier.FULL
    if _LIGHT_GREETING.search(text) or _LIGHT_CAPABILITIES.search(text):
        return PromptTier.LIGHT
    if include_web_tools and len(text) > 120:
        return PromptTier.FULL
    return PromptTier.STANDARD


def trim_env_block(env_block: str, tier: PromptTier) -> str:
    if not env_block or tier == PromptTier.FULL:
        return env_block
    lines = env_block.splitlines()
    if tier == PromptTier.LIGHT:
        keep = []
        for line in lines:
            if any(
                k in line
                for k in (
                    "Режим:",
                    "Ты:",
                    "Канал заметок:",
                    "Vault Obsidian:",
                )
            ):
                keep.append(line)
        return "\n".join(keep[:8])
    # STANDARD: drop long group/dm history sections
    out: list[str] = []
    skip = False
    for line in lines:
        if "Недавно в группе" in line or "Недавний диалог" in line:
            skip = True
            continue
        if skip and line.startswith("- "):
            continue
        skip = False
        out.append(line)
    return "\n".join(out)


def trim_history_block(history_block: str, tier: PromptTier) -> str:
    if not history_block:
        return ""
    lines = [ln for ln in history_block.splitlines() if ln.strip()]
    limit = {"light": 4, "standard": 10, "full": 20}[tier.value]
    trimmed = lines[-limit:]
    if not trimmed:
        return ""
    return "\n\n## НЕДАВНИЙ ДИАЛОГ\n" + "\n".join(trimmed) + "\n"


def trim_soul(soul: str, tier: PromptTier) -> str:
    if tier == PromptTier.FULL or not soul:
        return soul
    lines = [ln for ln in soul.splitlines() if ln.strip()]
    max_lines = 22 if tier == PromptTier.STANDARD else 12
    return "\n".join(lines[:max_lines])


def light_goal_directive() -> str:
    return (
        "Отвечай живым языком от первого лица. "
        "На приветствия и вопросы о себе — без инструментов. "
        "Инструменты только при явной просьбе что-то сделать."
    )


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


def build_system_prompt(
    *,
    tier: PromptTier,
    human_name: str,
    designation: str,
    soul: str,
    env_block: str,
    history_block: str,
    memory_block: str,
    output_hints: str,
    include_web_tools: bool,
    user_id: str,
) -> str:
    goal = light_goal_directive() if tier == PromptTier.LIGHT else GOAL_DIRECTIVE
    protocol = "" if tier == PromptTier.LIGHT else f"\n\n{TELEGRAM_AGENT_PROTOCOL}"
    html_fmt = TELEGRAM_HTML_FORMAT
    web_hint = WEB_TOOL_HINT if include_web_tools and tier == PromptTier.FULL else ""
    hints = f"\n\n{output_hints}" if output_hints and tier != PromptTier.LIGHT else ""

    return (
        f"{goal}{protocol}\n\n{html_fmt}\n\n"
        f"Ты — <b>{human_name}</b>, {designation}.\n\n"
        f"{trim_soul(soul, tier)}"
        f"{trim_env_block(env_block, tier)}"
        f"{trim_history_block(history_block, tier)}"
        f"{memory_block}"
        f"{web_hint}{hints}\n\n"
        f"user_id для инструментов: {user_id}"
    )


def tools_for_tier(tool_list: list, tier: PromptTier) -> list:
    """LIGHT: no tools; STANDARD: memory/tasks only; FULL: all tools."""
    if tier == PromptTier.LIGHT:
        return []
    if tier == PromptTier.STANDARD:
        allowed = frozenset({"remember_about_user", "list_tasks"})
        return [t for t in tool_list if t.name in allowed]
    return tool_list


_MEMORY_META = re.compile(
    r"(?i)"
    r"(?:ты\s+)?(?:можешь|умеешь)\s+запоминать"
    r"|(?:ты\s+)?(?:можешь|умеешь)\s+запомнить"
    r"|ты\s+помнишь(?:\s+меня)?"
    r"|помнишь\s+меня"
    r"|есть\s+ли\s+у\s+тебя\s+память"
)


def is_memory_meta_question(message: str) -> bool:
    """«Можешь запоминать?» — FAQ без LLM и без вызова remember tool."""
    text = (message or "").strip()
    if not text or _ACTION_PATTERN.search(text):
        return False
    return bool(_MEMORY_META.search(text))


def is_pure_greeting(message: str) -> bool:
    """Pure hello/thanks — no LLM needed for orchestrator."""
    text = (message or "").strip()
    return bool(text and _LIGHT_GREETING.match(text))


def is_capabilities_question(message: str) -> bool:
    text = (message or "").strip().lower()
    return bool(
        re.search(
            r"(расскажи|опиши|покажи|что ты можешь|чем можешь|чем ты можешь|"
            r"твои возможности|что умеешь|чем помочь)",
            text,
        )
        and not _ACTION_PATTERN.search(text)
    )
