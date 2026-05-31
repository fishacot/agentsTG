"""Tests for LLM client helpers and provider chain."""

import json

import pytest

from src.agents_tg.services.llm_client import (
    LLMClient,
    QwenAPIError,
    RateLimitError,
    parse_retry_after_seconds,
)


def test_parse_retry_after_from_groq_body():
    body = json.dumps(
        {
            "error": {
                "message": "Rate limit ... Please try again in 2.67s.",
            }
        }
    )
    assert parse_retry_after_seconds(body) == 2.67


def test_parse_retry_after_missing():
    assert parse_retry_after_seconds('{"error": {"message": "fail"}}') is None


def test_chain_order_gemini_then_groq(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "gemini,groq")

    from src.agents_tg.config.settings import AppSettings

    AppSettings()
    client = LLMClient()
    chain = client._chain()
    assert [p.name for p in chain] == ["gemini", "groq"]


def test_chain_skips_missing_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "gemini,groq")

    from src.agents_tg.config.settings import AppSettings

    AppSettings()
    client = LLMClient()
    chain = client._chain()
    assert [p.name for p in chain] == ["groq"]


@pytest.mark.asyncio
async def test_chat_completion_fallback_on_rate_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g1")
    monkeypatch.setenv("GROQ_API_KEY", "g2")
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "gemini,groq")

    from src.agents_tg.config.settings import AppSettings

    AppSettings()
    client = LLMClient()

    gemini = client._providers["gemini"]
    groq = client._providers["groq"]

    async def gemini_fail(*args, **kwargs):
        raise RateLimitError("429", status=429, retryable=True)

    async def groq_ok(*args, **kwargs):
        return {"content": "ok from groq", "tool_calls": []}

    gemini.chat_completion = gemini_fail
    groq.chat_completion = groq_ok

    result = await client.chat_completion(
        [{"role": "user", "content": "hi"}],
        agent_key="general",
    )
    assert result["content"] == "ok from groq"


@pytest.mark.asyncio
async def test_chat_completion_fallback_on_provider_error(monkeypatch):
    """Geo-block / bad key on Gemini should fall through to Groq."""
    monkeypatch.setenv("GEMINI_API_KEY", "g1")
    monkeypatch.setenv("GROQ_API_KEY", "g2")
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "gemini,groq")

    from src.agents_tg.config.settings import AppSettings

    AppSettings()
    client = LLMClient()

    gemini = client._providers["gemini"]
    groq = client._providers["groq"]

    async def gemini_geo_block(*args, **kwargs):
        raise QwenAPIError("API error (gemini): 400", status=400, retryable=False)

    async def groq_ok(*args, **kwargs):
        return {"content": "ok from groq", "tool_calls": []}

    gemini.chat_completion = gemini_geo_block
    groq.chat_completion = groq_ok

    result = await client.chat_completion(
        [{"role": "user", "content": "hi"}],
        agent_key="personal_assistant",
    )
    assert result["content"] == "ok from groq"


@pytest.mark.asyncio
async def test_all_providers_fail_raises_rate_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g1")
    monkeypatch.setenv("GROQ_API_KEY", "g2")
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "gemini,groq")

    from src.agents_tg.config.settings import AppSettings

    AppSettings()
    client = LLMClient()

    async def fail(*args, **kwargs):
        raise RateLimitError("429", status=429, retryable=True)

    for p in client._chain():
        p.chat_completion = fail

    with pytest.raises(RateLimitError):
        await client.chat_completion([{"role": "user", "content": "hi"}])
