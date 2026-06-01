"""Tests for proactive policy per agent."""

from src.agents_tg.services.proactive_policy import (
    allows_heartbeat,
    allows_project_checkin,
    get_proactive_policy,
)


def test_pa_full_proactive():
    p = get_proactive_policy("personal_assistant")
    assert p.heartbeat is True
    assert p.morning_digest is True
    assert p.cron_reminders is True


def test_orchestrator_project_checkin_only():
    assert allows_heartbeat("orchestrator") is False
    assert allows_project_checkin("orchestrator") is True


def test_research_no_proactive():
    assert allows_heartbeat("research") is False
    assert allows_project_checkin("research") is False
