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
# Greetings and meta — minimal prompt, no tools (LLM still answers)
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
    r"(?:расскажи|опиши|покажи|скажи).{0,40}(?:"
    r"что ты можешь|чем можешь|чем ты можешь|твои возможности|что умеешь|чем помочь"
    r")",
    re.IGNORECASE,
)
# News, digests, general knowledge — conversation only, no tools (avoid wrong list_tasks)
_CONVERSATION_INFO = re.compile(
    r"(?i)"
    r"(?:новост|сводк|digest|что\s+нового|актуальн|сегодня\s+в|"
    r"расскажи\s+про|объясни|что\s+такое|как\s+работает)"
)

_TASK_LIST_PATTERN = re.compile(
    r"(?i)(список\s+дел|мои\s+задачи|покажи\s+(?:мои\s+)?дела|"
    r"что\s+в\s+задачах|list\s+tasks|мои\s+дела)"
)
_RESEARCH_ACTION_PATTERN = re.compile(
    r"(?i)(найди|найти|поиск|исследуй|research|deep_research|"
    r"сводк|новост|актуальн|best practices|сравни|подбери|"
    r"источник|ссылк|what'?s new|загугли|в интернете)"
)

# Explicit actions — full tools + soul
_ACTION_PATTERN = re.compile(
    r"(?i)("
    r"создай|создать|запиши|записать|сохрани|сохранить"
    r"|найди|найти|поиск|исследуй|research"
    r"|добавь задач|список дел|list tasks|покажи\s+(?:мои\s+)?дела"
    r"|запомни что|remember"
    r"|deep_research|заметк"
    r"|напомни|напомин|пингни|пингани|каждый\s+день|ежедневн"
    r"|автономн|24\s*/\s*7|по\s+расписан"
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
    if (
        _LIGHT_GREETING.search(text)
        or _LIGHT_CAPABILITIES.search(text)
        or _CONVERSATION_INFO.search(text)
    ):
        return PromptTier.LIGHT
    if include_web_tools and len(text) > 120:
        if _RESEARCH_ACTION_PATTERN.search(text) or _ACTION_PATTERN.search(text):
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
        "Отвечай живым языком от первого лица — каждый раз по-новому, "
        "с учётом контекста и soul. "
        "На приветствия, «кто ты», возможности, память, новости — только разговор, "
        "без инструментов. "
        "Инструменты — только при явной просьбе что-то сделать (записать, задача, список дел)."
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
    user_message: str = "",
) -> str:
    goal = light_goal_directive() if tier == PromptTier.LIGHT else GOAL_DIRECTIVE
    protocol = "" if tier == PromptTier.LIGHT else f"\n\n{TELEGRAM_AGENT_PROTOCOL}"
    html_fmt = TELEGRAM_HTML_FORMAT
    show_web = (
        include_web_tools
        and tier == PromptTier.FULL
        and _RESEARCH_ACTION_PATTERN.search(user_message or "")
    )
    web_hint = WEB_TOOL_HINT if show_web else ""
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


def tools_for_tier(
    tool_list: list,
    tier: PromptTier,
    user_message: str = "",
    *,
    include_web_tools: bool = False,
) -> list:
    """LIGHT: no tools. STANDARD: remember only (+ list_tasks if asked).

    FULL (PA): all domain tools. FULL (web): deep_research only on explicit search.
    """
    if tier == PromptTier.LIGHT:
        return []
    if tier == PromptTier.STANDARD:
        allowed = {
            "remember_about_user",
            "log_project_activity",
            "update_project_status",
        }
        if not include_web_tools and _TASK_LIST_PATTERN.search(user_message or ""):
            allowed.add("list_tasks")
        if not include_web_tools and re.search(
            r"(?i)напомни|напомин|пинг|каждый\s+день|ежедневн|автоном",
            user_message or "",
        ):
            allowed.add("schedule_reminder")
        return [t for t in tool_list if t.name in allowed]
    if include_web_tools:
        allowed = {"remember_about_user"}
        if _RESEARCH_ACTION_PATTERN.search(user_message or ""):
            allowed.add("deep_research")
        return [t for t in tool_list if t.name in allowed]
    return tool_list
