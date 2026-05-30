"""Tests for per-agent delivery profiles."""

from src.agents_tg.services.agent_delivery_profile import get_delivery_profile


def test_coder_has_higher_max_tokens():
    profile = get_delivery_profile("coder")
    assert profile.max_tokens >= 1536
    assert profile.max_tool_rounds >= 2


def test_personal_assistant_high_autonomy():
    profile = get_delivery_profile("personal_assistant")
    assert profile.autonomy_level == "high"
    assert profile.max_tool_rounds >= 3
