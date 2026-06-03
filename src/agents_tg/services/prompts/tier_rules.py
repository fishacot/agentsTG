"""Regex-based prompt tier detection and trimming rules."""

from __future__ import annotations

import re
from enum import Enum

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

TASK_LIST_PATTERN = re.compile(
    r"(?i)(список\s+дел|мои\s+задачи|покажи\s+(?:мои\s+)?дела|"
    r"что\s+в\s+задачах|list\s+tasks|мои\s+дела)"
)
RESEARCH_ACTION_PATTERN = re.compile(
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


def detect_prompt_tier(
    user_message: str, *, include_web_tools: bool = False
) -> PromptTier:
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
        if RESEARCH_ACTION_PATTERN.search(text) or _ACTION_PATTERN.search(text):
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
        if not include_web_tools and TASK_LIST_PATTERN.search(user_message or ""):
            allowed.add("list_tasks")
        if not include_web_tools and re.search(
            r"(?i)напомни|напомин|пинг|каждый\s+день|ежедневн|автоном",
            user_message or "",
        ):
            allowed.add("schedule_reminder")
        return [t for t in tool_list if t.name in allowed]
    if include_web_tools:
        allowed = {"remember_about_user"}
        if RESEARCH_ACTION_PATTERN.search(user_message or ""):
            allowed.add("deep_research")
        return [t for t in tool_list if t.name in allowed]
    return tool_list
