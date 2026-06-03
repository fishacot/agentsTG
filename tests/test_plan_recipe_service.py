"""Plan recipe store (in-memory)."""

import pytest

from src.agents_tg.services.plan_recipe_service import (
    PlanRecipeService,
    intent_hash,
)


@pytest.fixture
def svc() -> PlanRecipeService:
    return PlanRecipeService()


@pytest.mark.asyncio
async def test_save_and_list_recipe(svc: PlanRecipeService):
    steps = [
        {"agent_key": "research", "instruction": "Найди источники"},
        {"agent_key": "coder", "instruction": "Сводка в код"},
    ]
    saved = await svc.save_recipe(
        user_id=1,
        intent_sample="Сделай обзор API",
        steps_json=steps,
    )
    assert saved is not None
    assert saved.success_count == 1

    again = await svc.save_recipe(
        user_id=1,
        intent_sample="Сделай обзор API",
        steps_json=steps,
    )
    assert again is not None
    assert again.success_count == 2

    listed = await svc.list_recipes(user_id=1, limit=5)
    assert len(listed) == 1
    assert listed[0].steps_json[0]["agent_key"] == "research"


@pytest.mark.asyncio
async def test_find_by_intent(svc: PlanRecipeService):
    await svc.save_recipe(
        user_id=2,
        intent_sample="План маркетинга",
        steps_json=[{"agent_key": "marketing", "instruction": "a"}],
    )
    found = await svc.find_by_intent(user_id=2, intent_sample="План маркетинга")
    assert found is not None
    assert found.intent_hash == intent_hash("План маркетинга")


def test_intent_hash_stable():
    assert intent_hash("Hello  World") == intent_hash("hello world")
