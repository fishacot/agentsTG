"""Tests for user tasks service."""

import pytest

from src.agents_tg.services.user_tasks_service import user_tasks_service


@pytest.mark.asyncio
async def test_add_and_list_tasks_memory():
    uid = 424242
    added = await user_tasks_service.add_task(
        telegram_user_id=uid, title="Купить молоко", due_date="завтра"
    )
    assert added["ok"] is True
    listed = await user_tasks_service.list_tasks(telegram_user_id=uid)
    assert len(listed["tasks"]) >= 1
    assert listed["tasks"][-1]["title"] == "Купить молоко"
