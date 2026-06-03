"""Gateway A2A callback → plan_executor context."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents_tg.gateway.router import gateway_router


@pytest.mark.asyncio
async def test_handle_a2a_callback_updates_plan_context():
    payload = {
        "job_id": "job-1",
        "status": "done",
        "result_summary": "ok",
        "task_id": "task-1",
        "step_index": 1,
    }
    with (
        patch(
            "src.agents_tg.gateway.router.job_store.get",
            new_callable=AsyncMock,
            return_value={"id": "job-1"},
        ),
        patch(
            "src.agents_tg.gateway.router.job_store.transition",
            new_callable=AsyncMock,
        ),
        patch(
            "src.agents_tg.services.plan_executor.plan_executor.update_task_context",
            new_callable=AsyncMock,
        ) as mock_ctx,
        patch(
            "src.agents_tg.services.plan_executor.plan_executor.on_a2a_step_callback",
            new_callable=AsyncMock,
            return_value={"ok": True, "resumed": False, "complete": False},
        ) as mock_plan,
    ):
        result = await gateway_router.handle_a2a_callback(payload)
        assert result["ok"] is True
        mock_ctx.assert_awaited_once()
        mock_plan.assert_awaited_once()
        patch_arg = mock_ctx.await_args[0][1]
        assert patch_arg["current_step"] == 1
        assert patch_arg["a2a_callback"]["step_index"] == 1
        assert result["plan"]["resumed"] is False
