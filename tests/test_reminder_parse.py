"""Tests for reminder time parsing."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.agents_tg.services.reminder_parse import parse_reminder_when


def test_parse_through_minutes(monkeypatch):
    base = datetime(2026, 5, 30, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    def fake_now():
        return base

    monkeypatch.setattr("src.agents_tg.services.reminder_parse.now_local", fake_now)
    dt = parse_reminder_when("через 5 минут")
    assert dt is not None
    assert dt.hour == 10 and dt.minute == 5


def test_parse_at_hour(monkeypatch):
    base = datetime(2026, 5, 30, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))

    monkeypatch.setattr("src.agents_tg.services.reminder_parse.now_local", lambda: base)
    dt = parse_reminder_when("в 11:00")
    assert dt is not None
    assert dt.hour == 11 and dt.minute == 0
