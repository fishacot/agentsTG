"""LLM client applies STEP_MODEL_ROUTING from step_kind context."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents_tg.services.llm_context import set_llm_step_kind
from src.agents_tg.services.llm_step_routing import (
    clear_routing_cache,
    parse_step_model_routing,
)


@pytest.fixture(autouse=True)
def _clear_routing():
    clear_routing_cache()
    yield
    clear_routing_cache()


@pytest.mark.asyncio
async def test_chat_completion_uses_step_routing_override():
    parse_step_model_routing('{"finalize":"override-model"}')
    set_llm_step_kind("finalize")

    mock_provider = MagicMock()
    mock_provider.name = "groq"
    mock_provider.available = True
    mock_provider.chat_completion = AsyncMock(
        return_value={"content": "ok", "tool_calls": []}
    )

    from src.agents_tg.services.llm_client import LLMClient

    client = LLMClient()
    with patch.object(client, "_chain", return_value=[mock_provider]):
        with patch(
            "src.agents_tg.services.llm_budget.llm_budget.is_exhausted",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch(
                "src.agents_tg.services.llm_budget.llm_budget.record",
                new_callable=AsyncMock,
            ):
                await client.chat_completion(
                    [{"role": "user", "content": "hi"}],
                    agent_key="coder",
                )

    call_kwargs = mock_provider.chat_completion.await_args.kwargs
    assert call_kwargs["model"] == "override-model"
