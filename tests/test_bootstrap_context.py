"""Tests for OpenClaw bootstrap blocks."""

import pytest

import src.agents_tg.services.bootstrap_context as bootstrap_context
from src.agents_tg.services.bootstrap_context import (
    build_focus_block,
    build_time_block,
    build_user_block,
)
from src.agents_tg.services.prompt_builder import PromptTier
from src.agents_tg.services.shared_context import SharedContextService


@pytest.fixture
def svc(monkeypatch) -> SharedContextService:
    service = SharedContextService()
    monkeypatch.setattr(bootstrap_context, "shared_context", service)
    return service


@pytest.mark.asyncio
async def test_time_block_contains_msk():
    block = build_time_block()
    assert "МСК" in block or "Europe" in block or ":" in block


@pytest.mark.asyncio
async def test_user_block_light_with_name(svc: SharedContextService):
    await svc.update_profile(1, address_as="Друг")
    block = await build_user_block(1, tier=PromptTier.LIGHT)
    assert "Друг" in block


@pytest.mark.asyncio
async def test_focus_block_with_project(svc: SharedContextService):
    await svc.set_active_project(1, title="Сайт о собаках")
    await svc.log_activity(1, agent_key="coder", summary="HTML главной", kind="code")
    block = await build_focus_block(1, tier=PromptTier.STANDARD)
    assert "Сайт о собаках" in block
    assert "HTML" in block or "coder" in block.lower() or "Руслан" in block
