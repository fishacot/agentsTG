"""Tests for L2 gateway router and job store."""

import pytest

from src.agents_tg.gateway.envelope import OpenClawEnvelope
from src.agents_tg.gateway.job_store import job_store
from src.agents_tg.gateway.router import gateway_router


@pytest.mark.asyncio
async def test_dispatch_creates_job():
    env = OpenClawEnvelope(
        chat_id=100,
        user_id=7,
        text="test",
        message_id=1,
        agent_key="orchestrator",
    )
    result = await gateway_router.dispatch(env)
    assert result.duplicate is False
    assert result.session_id
    assert result.job_id
    await gateway_router.complete_job(result.job_id)


@pytest.mark.asyncio
async def test_idempotency_via_job_store():
    key = "coder:100:99"
    job_store._idempotency.pop(key, None)
    first = await job_store.create(
        user_id=7,
        agent_key="coder",
        trigger="test",
        idempotency_key=key,
    )
    second = await job_store.create(
        user_id=7,
        agent_key="coder",
        trigger="test",
        idempotency_key=key,
    )
    assert first["id"] == second["id"]
