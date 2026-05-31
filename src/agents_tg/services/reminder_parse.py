"""Parse natural-language reminder times in MSK."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from src.agents_tg.utils.timezone_utils import get_app_tz, now_local


def parse_reminder_when(text: str, *, base: datetime | None = None) -> datetime | None:
    """Parse when-string to aware datetime in app timezone."""
    raw = (text or "").strip().lower()
    if not raw:
        return None

    base_local = base or now_local()
    tz = get_app_tz()

    # через N минут/мин/м
    m = re.search(r"через\s+(\d+)\s*(мин|минут|минуты|м\b|minute)", raw)
    if m:
        return base_local + timedelta(minutes=int(m.group(1)))

    m = re.search(r"через\s+(\d+)\s*(час|часа|часов|ч\b|hour)", raw)
    if m:
        return base_local + timedelta(hours=int(m.group(1)))

    # в HH:MM or в H
    m = re.search(r"(?:в|at)\s*(\d{1,2})(?::(\d{2}))?\s*(?:утра|утром|дня|вечера|мск)?", raw)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        if "вечера" in raw and hour < 12:
            hour += 12
        if "дня" in raw and hour < 12 and hour != 12:
            hour += 12
        target = base_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= base_local:
            target += timedelta(days=1)
        return target

    # завтра в HH:MM
    if "завтра" in raw:
        m = re.search(r"(\d{1,2})(?::(\d{2}))?", raw)
        hour = int(m.group(1)) if m else 9
        minute = int(m.group(2) or 0) if m and m.group(2) else 0
        tomorrow = (base_local + timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return tomorrow

    # ISO-ish
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    except ValueError:
        pass

    return None
