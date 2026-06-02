"""Tests for Manus verify-lite pass."""

import pytest

from src.agents_tg.services.verify_step import verify_step_result


@pytest.mark.asyncio
async def test_verify_ok_on_normal_text():
    vr = await verify_step_result(
        instruction="find news",
        step_summary="Вот краткий обзор новостей Python.",
        agent_key="research",
    )
    assert vr.ok is True


@pytest.mark.asyncio
async def test_verify_replan_on_empty():
    vr = await verify_step_result(
        instruction="x",
        step_summary="",
        agent_key="coder",
    )
    assert vr.ok is False
    assert vr.suggest_replan is True


@pytest.mark.asyncio
async def test_verify_blocks_supervisor_json():
    vr = await verify_step_result(
        instruction="route",
        step_summary='{"action_type": "delegate", "plan": []}',
        agent_key="orchestrator",
    )
    assert vr.ok is False
    assert vr.suggest_replan is True
