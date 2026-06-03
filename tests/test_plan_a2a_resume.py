"""Plan executor A2A callback and resume registration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents_tg.services.plan_executor import PlanExecutor, PlanTask


@pytest.mark.asyncio
async def test_on_a2a_step_callback_marks_done_and_sets_resume():
    pe = PlanExecutor()
    pe._memory_tasks["t1"] = {
        "id": "t1",
        "status": "running",
        "context_json": {},
    }
    pe._memory_steps["t1"] = [
        {
            "step_index": 0,
            "agent_key": "research",
            "instruction": "a",
            "status": "running",
        },
        {
            "step_index": 1,
            "agent_key": "coder",
            "instruction": "b",
            "status": "pending",
        },
    ]
    with patch.object(
        pe, "_try_resume_registered_plan", new_callable=AsyncMock
    ) as mock_resume:
        mock_resume.return_value = False
        result = await pe.on_a2a_step_callback(
            "t1", step_index=0, status="done", summary="ok"
        )
    assert result["ok"] is True
    assert result["next_step"] == 1
    assert pe._memory_steps["t1"][0]["status"] == "done"


@pytest.mark.asyncio
async def test_on_a2a_resumes_when_handle_registered():
    pe = PlanExecutor()
    task = PlanTask(
        task_id="t2",
        user_id=1,
        title="x",
        steps=[("research", "a"), ("coder", "b")],
    )
    pe._memory_steps["t2"] = [
        {
            "step_index": 0,
            "agent_key": "research",
            "instruction": "a",
            "status": "pending",
        },
        {
            "step_index": 1,
            "agent_key": "coder",
            "instruction": "b",
            "status": "pending",
        },
    ]
    pe._memory_tasks["t2"] = {"id": "t2", "status": "running", "context_json": {}}
    msg = MagicMock()
    pe.register_plan_resume(
        "t2",
        task=task,
        message=msg,
        user_text="hi",
        process_fn=AsyncMock(),
    )
    with patch.object(
        pe, "_try_resume_registered_plan", new_callable=AsyncMock
    ) as mock_resume:
        mock_resume.return_value = True
        result = await pe.on_a2a_step_callback(
            "t2", step_index=0, status="done", summary="ext"
        )
    assert result["resumed"] is True
    assert result["next_step"] == 1
    mock_resume.assert_awaited_once_with("t2", start_index=1)
