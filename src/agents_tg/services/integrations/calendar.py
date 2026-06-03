"""Calendar integration — CalDAV URL or stub for local MVP."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.integrations.base import IntegrationError, audit_integration


def _ics_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\n", r"\n")
    )


def _write_ics_file(*, user_id: str, title: str, start: datetime, end: datetime) -> str:
    """Write .ics under workspace for import into any calendar app."""
    settings = get_settings()
    safe_uid = re.sub(r"[^\w-]", "_", user_id)[:64] or "user"
    base = (
        Path(settings.OBSIDIAN_VAULT_PATH).parent
        / "workspace"
        / "users"
        / safe_uid
        / "calendar"
    )
    base.mkdir(parents=True, exist_ok=True)
    stamp = start.strftime("%Y%m%dT%H%M%S")
    fname = f"{stamp}_{uuid.uuid4().hex[:8]}.ics"
    path = base / fname
    uid = f"{uuid.uuid4()}@agents-tg"
    dtstamp = datetime.now(start.tzinfo or ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%S")
    start_s = start.strftime("%Y%m%dT%H%M%S")
    end_s = end.strftime("%Y%m%dT%H%M%S")
    body = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//agentsTG//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{start_s}",
            f"DTEND:{end_s}",
            f"SUMMARY:{_ics_escape(title)}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")
    return str(path.as_posix())


async def create_calendar_event(
    *,
    user_id: str,
    title: str,
    start_at: str | None = None,
    duration_minutes: int = 60,
) -> dict[str, Any]:
    """Create event. Uses CALDAV_URL when set; otherwise returns structured stub."""
    settings = get_settings()
    tz = ZoneInfo(settings.APP_TIMEZONE or "Europe/Moscow")
    if start_at:
        try:
            start = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=tz)
        except ValueError as exc:
            raise IntegrationError(f"invalid start_at: {start_at}") from exc
    else:
        start = datetime.now(tz) + timedelta(days=1)
        start = start.replace(hour=15, minute=0, second=0, microsecond=0)

    end = start + timedelta(minutes=duration_minutes)
    event = {
        "title": title[:200],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": str(tz),
    }

    ics_path = _write_ics_file(
        user_id=user_id, title=event["title"], start=start, end=end
    )
    event["ics_path"] = ics_path

    caldav_url = (settings.CALDAV_URL or "").strip()
    if caldav_url:
        audit_integration("calendar", user_id=user_id, detail=f"ics+caldav_url {title}")
        return {
            "ok": True,
            "mode": "ics_export",
            "event": event,
            "note": (
                "Событие сохранено в .ics; импортируйте в календарь. "
                "Прямая запись CalDAV — в следующем релизе."
            ),
        }

    audit_integration("calendar", user_id=user_id, detail=f"ics local {title}")
    return {
        "ok": True,
        "mode": "ics_export",
        "event": event,
        "note": "Файл .ics создан — откройте или импортируйте в календарь.",
    }
