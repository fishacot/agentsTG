"""STEP_MODEL_ROUTING parser."""

import pytest

from src.agents_tg.services.llm_step_routing import (
    clear_routing_cache,
    parse_step_model_routing,
    resolve_step_model,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_routing_cache()
    yield
    clear_routing_cache()


def test_parse_valid_json():
    table = parse_step_model_routing(
        '{"classify":"llama-3.1-8b-instant","finalize":"gemini-2.5-flash"}'
    )
    assert table["classify"] == "llama-3.1-8b-instant"
    assert table["finalize"] == "gemini-2.5-flash"


def test_parse_invalid_json_returns_empty():
    assert parse_step_model_routing("{not json") == {}


def test_resolve_step_model():
    parse_step_model_routing('{"finalize":"big-model"}')
    assert resolve_step_model("finalize") == "big-model"
    assert resolve_step_model("unknown") is None


def test_resolve_agent_composite_key():
    parse_step_model_routing('{"orchestrator:finalize":"orch-model"}')
    assert resolve_step_model("finalize", agent_key="orchestrator") == "orch-model"
