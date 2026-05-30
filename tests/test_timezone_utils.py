"""Tests for timezone_utils."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.agents_tg.utils import timezone_utils


def test_now_local_display_contains_msk(monkeypatch):
    class FakeSettings:
        APP_TIMEZONE = "Europe/Moscow"

    monkeypatch.setattr(timezone_utils, "get_settings", lambda: FakeSettings())
    display = timezone_utils.now_local_display()
    assert "МСК" in display


def test_local_to_utc_moscow():
    msk = ZoneInfo("Europe/Moscow")
    local = datetime(2026, 5, 30, 11, 0, tzinfo=msk)
    utc = timezone_utils.local_to_utc(local)
    assert utc.hour == 8
    assert utc.tzinfo == timezone.utc
