"""Tests for orchestrator project binding."""

import pytest

from src.agents_tg.services.orchestrator_project import (
    extract_project_title,
    maybe_bind_plan_to_project,
)
from src.agents_tg.services.shared_context import SharedContextService


def test_extract_title_from_message():
    title = extract_project_title(
        "делаем сайт о собаках: парсинг и html",
        ["парсинг", "html"],
    )
    assert "собак" in title.lower()


@pytest.mark.asyncio
async def test_bind_plan_creates_project(monkeypatch):
    svc = SharedContextService()

    import src.agents_tg.services.orchestrator_project as op

    monkeypatch.setattr(op, "shared_context", svc)

    await maybe_bind_plan_to_project(
        "99",
        "делаем сайт о собаках",
        ["Ульяна: парсинг", "Руслан: html"],
    )
    active = await svc.get_active_project(99)
    assert active is not None
    activities = await svc.get_recent_activity(99)
    assert any(a["kind"] == "delegation" for a in activities)
