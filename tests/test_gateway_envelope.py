"""Tests for OpenClaw envelope (Phase 1)."""

from src.agents_tg.gateway.envelope import MediaItem, OpenClawEnvelope


def test_envelope_idempotency_key():
    env = OpenClawEnvelope(
        chat_id=1,
        user_id=42,
        text="hello",
        message_id=99,
        agent_key="personal_assistant",
    )
    assert env.idempotency_key == "personal_assistant:1:99"


def test_envelope_media_round_trip():
    env = OpenClawEnvelope(
        chat_id=1,
        user_id=42,
        text="",
        media=[MediaItem(kind="voice", placeholder="[voice]")],
        message_id=1,
        agent_key="research",
    )
    assert env.media[0].kind == "voice"
