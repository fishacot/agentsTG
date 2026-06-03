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


@pytest.mark.asyncio
async def test_verify_schema_browser_missing_status():
    vr = await verify_step_result(
        instruction="open page",
        step_summary="Page loaded fine with title Example.",
        agent_key="research",
        tool_results=[
            {"tool": "browser_navigate", "result": {"ok": True, "title": "Example"}},
        ],
    )
    assert vr.ok is False
    assert "status_code" in (vr.issues or "")


@pytest.mark.asyncio
async def test_verify_schema_ok_with_status():
    vr = await verify_step_result(
        instruction="open page",
        step_summary="Page loaded fine with title Example.",
        agent_key="research",
        tool_results=[
            {
                "tool": "browser_navigate",
                "result": {"ok": True, "status_code": 200, "title": "Example"},
            },
        ],
    )
    assert vr.ok is True


@pytest.mark.asyncio
async def test_verify_schema_fail_on_bad_tool():
    vr = await verify_step_result(
        instruction="browse",
        step_summary="Страница загружена.",
        agent_key="research",
        tool_results=[
            {"tool": "browser_navigate", "result": {"ok": True, "title": "x"}}
        ],
    )
    assert vr.ok is False
    assert vr.suggest_replan is True
