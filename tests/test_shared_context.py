"""Tests for shared context service (in-memory)."""

import pytest

from src.agents_tg.services.shared_context import SharedContextService


@pytest.fixture
def svc() -> SharedContextService:
    return SharedContextService()


@pytest.mark.asyncio
async def test_profile_update(svc: SharedContextService):
    await svc.update_profile(
        42,
        display_name="Alex",
        address_as="Алекс",
        likes=["лаконичность"],
    )
    p = await svc.get_profile(42)
    assert p["display_name"] == "Alex"
    assert "лаконичность" in p["preferences"]["likes"]


@pytest.mark.asyncio
async def test_project_and_activity(svc: SharedContextService):
    proj = await svc.set_active_project(
        42, title="Сайт о собаках", description="landing"
    )
    assert proj["status"] == "active"
    await svc.log_activity(
        42,
        agent_key="research",
        summary="Нашла 10 источников",
        kind="research",
    )
    activities = await svc.get_recent_activity(42, limit=3)
    assert len(activities) == 1
    assert activities[0]["agent_key"] == "research"


@pytest.mark.asyncio
async def test_single_active_project(svc: SharedContextService):
    await svc.set_active_project(42, title="A")
    await svc.set_active_project(42, title="B")
    active = await svc.get_active_project(42)
    assert active["title"] == "B"
