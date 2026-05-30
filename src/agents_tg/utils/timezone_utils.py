"""Application timezone helpers (default Europe/Moscow)."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.agents_tg.config.settings import get_settings

_MSK_LABEL = "МСК"


def get_app_tz() -> ZoneInfo:
    """Return configured application timezone."""
    name = get_settings().APP_TIMEZONE.strip() or "Europe/Moscow"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Europe/Moscow")


def now_local() -> datetime:
    """Current time in application timezone (aware)."""
    return datetime.now(timezone.utc).astimezone(get_app_tz())


def now_local_display() -> str:
    """Human-readable local time for agent prompts."""
    dt = now_local()
    return dt.strftime(f"%d.%m.%Y %H:%M ({_MSK_LABEL})")


def utc_to_local(dt: datetime) -> datetime:
    """Convert aware datetime to application timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_app_tz())


def local_to_utc(dt: datetime) -> datetime:
    """Convert local aware datetime to UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_app_tz())
    return dt.astimezone(timezone.utc)


def format_local(dt: datetime, *, include_tz_label: bool = True) -> str:
    """Format datetime for user-facing messages."""
    local = utc_to_local(dt) if dt.tzinfo else dt.replace(tzinfo=get_app_tz())
    base = local.strftime("%d.%m.%Y %H:%M")
    if include_tz_label and get_settings().APP_TIMEZONE == "Europe/Moscow":
        return f"{base} ({_MSK_LABEL})"
    return base
