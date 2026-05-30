"""Tests for group coordinator anti-echo and NO_REPLY."""

from datetime import datetime, timezone

from src.agents_tg.bots.group_coordinator import GroupCoordinator, GroupMessage


def test_should_skip_echo_same_text():
    coord = GroupCoordinator()
    assert coord.should_skip_echo(1, "coder", "Hello") is False
    assert coord.should_skip_echo(1, "coder", "Hello") is True


def test_should_stay_silent_after_colleague():
    coord = GroupCoordinator()
    coord.add_message(
        1,
        GroupMessage(
            message_id=1,
            from_agent="user",
            text="найди новости",
            timestamp=datetime.now(timezone.utc),
            mentions=[],
        ),
    )
    coord.add_message(
        1,
        GroupMessage(
            message_id=2,
            from_agent="research",
            text="Вот новости...",
            timestamp=datetime.now(timezone.utc),
            mentions=[],
        ),
    )
    assert coord.should_stay_silent(1, "спасибо") is True
    assert coord.should_stay_silent(1, "найди ещё про Python asyncio") is False


def test_plan_storage():
    coord = GroupCoordinator()
    coord.set_plan(99, ["Шаг 1", "Шаг 2"])
    assert len(coord.get_plan(99)) == 2
    assert "1. Шаг 1" in coord.format_plan(99)
