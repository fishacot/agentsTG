"""Tests for DelegationEnvelope."""

from src.agents_tg.services.delegation_envelope import DelegationEnvelope


def test_envelope_roundtrip():
    env = DelegationEnvelope.from_plan_step(
        task_id="abc",
        requester_user_id=42,
        target_agent_id="research",
        instruction="найди новости",
    )
    data = env.to_dict()
    assert data["task_id"] == "abc"
    assert data["target_agent_id"] == "research"
    assert len(data["delegation_chain"]) == 1
