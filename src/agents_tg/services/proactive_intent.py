"""Materialize proactive schedules from natural language (behavior, not prompt-only)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from src.agents_tg.services.reminder_parse import parse_reminder_when
from src.agents_tg.utils.timezone_utils import format_local, now_local

# «каждый день в 11 утра», «ежедневно в 11:00 по мск»
_DAILY_TIME = re.compile(
    r"(?i)"
    r"(?:"
    r"(?:каждый\s+день|ежедневн\w*|every\s+day).{0,60}?"
    r"(?:в\s*)?(\d{1,2})(?::(\d{2}))?\s*(?:утра|утром|дня|вечера|мск|по\s+мск)?"
    r"|"
    r"(?:в\s*)?(\d{1,2})(?::(\d{2}))?\s*(?:утра|утром|мск|по\s+мск)?"
    r".{0,20}?(?:каждый\s+день|ежедневн\w*)"
    r")"
)

_ONE_SHOT_REMIND = re.compile(
    r"(?i)(?:напомни|напоминание|пингни|пингани)\s+(?:мне\s+)?(.+)"
)

_AUTONOMY_CUE = re.compile(
    r"(?i)"
    r"(?:автономн|24\s*/\s*7|сама\s+напишеш|сами?\s+пиш|без\s+моих\s+сообщ"
    r"|проактивн|по\s+расписан)"
)


def _extract_daily_time(text: str) -> tuple[int, int] | None:
    m = _DAILY_TIME.search(text)
    if not m:
        return None
    hour_s = m.group(1) or m.group(3)
    min_s = m.group(2) or m.group(4)
    if not hour_s:
        return None
    hour = int(hour_s)
    minute = int(min_s or 0)
    if "вечера" in text.lower() and hour < 12:
        hour += 12
    return hour, minute


def _default_daily_message(text: str) -> str:
    lower = text.lower()
    if "добр" in lower and "утр" in lower:
        return "Доброе утро!"
    if "good morning" in lower:
        return "Good morning!"
    return "Доброе утро!"


def _next_fire_at_local(hour: int, minute: int) -> datetime:
    local = now_local()
    target = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local >= target:
        target += timedelta(days=1)
    return target


async def try_schedule_from_message(
    message: str,
    *,
    telegram_user_id: int,
    chat_id: int,
    agent_key: str = "personal_assistant",
) -> list[str]:
    """Detect proactive scheduling intent and persist reminders before LLM reply.

    Returns human-readable lines for the system prompt (what was already scheduled).
    """
    if not message or not telegram_user_id or not chat_id:
        return []

    text = message.strip()
    if not (
        _AUTONOMY_CUE.search(text)
        or _DAILY_TIME.search(text)
        or _ONE_SHOT_REMIND.search(text)
    ):
        return []

    from src.agents_tg.services.reminder_service import reminder_service

    lines: list[str] = []

    daily = _extract_daily_time(text)
    if daily and (_DAILY_TIME.search(text) or _AUTONOMY_CUE.search(text)):
        hour, minute = daily
        body = _default_daily_message(text)
        fire_at = _next_fire_at_local(hour, minute)
        result = await reminder_service.schedule(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            text=body,
            fire_at_local=fire_at,
            agent_key=agent_key,
            recurrence="daily",
        )
        if result.get("ok"):
            lines.append(
                f"- Ежедневное автономное сообщение «{body}» в {hour:02d}:{minute:02d} МСK "
                f"(первый раз {result.get('fire_at_local', format_local(fire_at))}, id={result.get('id')})"
            )

    if not lines and _ONE_SHOT_REMIND.search(text):
        m = _ONE_SHOT_REMIND.search(text)
        tail = (m.group(1) if m else "").strip()
        when_part = tail
        body = tail
        for sep in (" — ", " - ", ": "):
            if sep in tail:
                parts = tail.split(sep, 1)
                when_part, body = parts[0].strip(), parts[1].strip()
                break
        fire_at = parse_reminder_when(when_part)
        if fire_at and body:
            result = await reminder_service.schedule(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                text=body,
                fire_at_local=fire_at,
                agent_key=agent_key,
                recurrence="once",
            )
            if result.get("ok"):
                lines.append(
                    f"- Напоминание «{body}» на {result.get('fire_at_local')} (id={result.get('id')})"
                )

    return lines


def build_scheduled_context(lines: list[str]) -> str:
    from src.agents_tg.services.prompts.memory_block import (
        build_scheduled_context as _build,
    )

    return _build(lines)
