"""Multi-provider LLM client with fallback chain (Gemini → Groq → HF)."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from typing import Any

import httpx

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_models import (
    AGENT_MODELS,
    MODEL_DEFAULT,
    get_model_for_provider,
)

logger = logging.getLogger(__name__)

_LLM_SEMAPHORE = asyncio.Semaphore(1)
_AGENT_SEMAPHORES: dict[str, asyncio.Semaphore] = {}


def _semaphore_for_agent(agent_key: str | None) -> asyncio.Semaphore:
    key = agent_key or "default"
    if key not in _AGENT_SEMAPHORES:
        _AGENT_SEMAPHORES[key] = asyncio.Semaphore(2)
    return _AGENT_SEMAPHORES[key]
_RETRYABLE_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 6
_BASE_DELAYS = (2.0, 3.0, 5.0, 8.0, 12.0, 15.0)


class QwenAPIError(Exception):
    """LLM inference API error."""

    def __init__(self, message: str, *, status: int = 0, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class RateLimitError(QwenAPIError):
    """Rate limit — try next provider or retry."""

    pass


def parse_retry_after_seconds(body: str) -> float | None:
    """Parse Groq/Gemini 'try again in Xs' from error JSON."""
    try:
        data = json.loads(body)
        msg = str(data.get("error", {}).get("message", ""))
    except (json.JSONDecodeError, AttributeError):
        msg = body
    match = re.search(r"try again in ([\d.]+)s", msg, re.I)
    if match:
        return float(match.group(1))
    return None


class _ProviderBase:
    name: str

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        model: str,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class GroqProvider(_ProviderBase):
    name = "groq"

    def __init__(self) -> None:
        self._session: httpx.AsyncClient | None = None

    @property
    def available(self) -> bool:
        return bool(get_settings().GROQ_API_KEY)

    @property
    def api_base(self) -> str:
        return get_settings().GROQ_API_BASE

    async def _session_client(self) -> httpx.AsyncClient:
        api_key = get_settings().GROQ_API_KEY
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._session

    async def chat_completion(self, messages, *, temperature, max_tokens, model, tools, tool_choice, response_format=None):
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        if response_format:
            payload["response_format"] = response_format
        raw = await _post_with_retry(self.api_base, payload, session=await self._session_client())
        return _extract_message(raw)


class GeminiProvider(_ProviderBase):
    name = "gemini"

    def __init__(self) -> None:
        self._session: httpx.AsyncClient | None = None

    @property
    def available(self) -> bool:
        return bool(get_settings().GEMINI_API_KEY)

    @property
    def api_base(self) -> str:
        return get_settings().GEMINI_API_BASE.rstrip("/")

    async def _session_client(self) -> httpx.AsyncClient:
        api_key = get_settings().GEMINI_API_KEY
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._session

    async def chat_completion(self, messages, *, temperature, max_tokens, model, tools, tool_choice, response_format=None):
        url = f"{self.api_base}/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        if response_format:
            payload["response_format"] = response_format
        raw = await _post_with_retry(url, payload, session=await self._session_client())
        return _extract_message(raw)


class HuggingFaceProvider(_ProviderBase):
    name = "huggingface"

    def __init__(self) -> None:
        self._session: httpx.AsyncClient | None = None

    @property
    def available(self) -> bool:
        return bool(get_settings().QWEN_API_KEY)

    @property
    def api_base(self) -> str:
        return get_settings().QWEN_API_BASE

    async def _session_client(self) -> httpx.AsyncClient:
        api_key = get_settings().QWEN_API_KEY
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._session

    async def chat_completion(self, messages, *, temperature, max_tokens, model, tools, tool_choice, response_format=None):
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        raw = await _post_with_retry(self.api_base, payload, session=await self._session_client())
        return _extract_message(raw)


async def _post_with_retry(
    url: str,
    payload: dict[str, Any],
    *,
    session: httpx.AsyncClient,
) -> Any:
    model = payload.get("model", "?")
    last_error: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code
            body = e.response.text[:800]
            if status not in _RETRYABLE_STATUS or attempt >= _MAX_ATTEMPTS - 1:
                break
            wait = parse_retry_after_seconds(body)
            if wait is None:
                wait = _BASE_DELAYS[min(attempt, len(_BASE_DELAYS) - 1)]
            wait += random.uniform(0.3, 1.2)
            logger.warning(
                "LLM rate limit model=%s status=%s attempt=%s/%s wait=%.1fs",
                model,
                status,
                attempt + 1,
                _MAX_ATTEMPTS - 1,
                wait,
            )
            await asyncio.sleep(wait)
        except Exception as e:
            last_error = e
            break

    if isinstance(last_error, httpx.HTTPStatusError):
        status = last_error.response.status_code
        body = last_error.response.text[:500]
        logger.error("LLM API error model=%s status=%s body=%s", model, status, body)
        retryable = status in _RETRYABLE_STATUS
        exc_cls = RateLimitError if status == 429 else QwenAPIError
        raise exc_cls(
            f"API error ({model}): {status}",
            status=status,
            retryable=retryable,
        ) from last_error

    raise QwenAPIError(f"Request failed: {last_error}", retryable=False) from last_error


def _extract_message(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            tool_calls = message.get("tool_calls")
            finish_reason = choices[0].get("finish_reason") or ""
            return {
                "content": str(content).strip() if content else "",
                "tool_calls": tool_calls or [],
                "finish_reason": finish_reason,
            }
        text = _extract_text(result)
        return {"content": text, "tool_calls": [], "finish_reason": ""}
    return {"content": str(result), "tool_calls": [], "finish_reason": ""}


def _extract_text(result: Any) -> str:
    if isinstance(result, dict):
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if content:
                return str(content).strip()
            text = choices[0].get("text")
            if text:
                return str(text).strip()
        generated = result.get("generated_text")
        if generated:
            return str(generated).strip()
    if isinstance(result, list) and result:
        item = result[0]
        if isinstance(item, dict):
            for key in ("generated_text", "text"):
                if item.get(key):
                    return str(item[key]).strip()
    return str(result)


class LLMClient:
    """Route requests through configured provider chain."""

    def __init__(self) -> None:
        self._providers: dict[str, _ProviderBase] = {
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            "huggingface": HuggingFaceProvider(),
        }
        self.default_model = get_settings().llm_default_model or MODEL_DEFAULT

    def model_for_agent(self, agent_key: str, provider_name: str) -> str:
        s = get_settings()
        override = s.get_agent_model_override(agent_key)
        if override:
            return override
        return get_model_for_provider(agent_key, provider_name)

    def _chain(self) -> list[_ProviderBase]:
        s = get_settings()
        names = s.llm_provider_chain_list
        out: list[_ProviderBase] = []
        for name in names:
            p = self._providers.get(name)
            if p and p.available:
                out.append(p)
        if not out:
            if s.GROQ_API_KEY:
                out.append(self._providers["groq"])
            elif s.GEMINI_API_KEY:
                out.append(self._providers["gemini"])
            elif s.QWEN_API_KEY:
                out.append(self._providers["huggingface"])
        return out

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        model: str | None = None,
        agent_key: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        result = await self.chat_completion(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            agent_key=agent_key,
            response_format=response_format,
        )
        return (result.get("content") or "").strip()

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        model: str | None = None,
        agent_key: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chain = self._chain()
        if not chain:
            raise QwenAPIError("No LLM provider configured (set GEMINI_API_KEY or GROQ_API_KEY)")

        errors: list[str] = []
        sem = _semaphore_for_agent(agent_key)
        async with sem:
            for idx, provider in enumerate(chain):
                resolved = model or self.model_for_agent(agent_key or "", provider.name)
                has_next = idx < len(chain) - 1
                try:
                    return await provider.chat_completion(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        model=resolved,
                        tools=tools,
                        tool_choice=tool_choice,
                        response_format=response_format,
                    )
                except RateLimitError as exc:
                    errors.append(f"{provider.name}:{exc.status or 429}")
                    logger.warning("Provider %s rate limited, trying next", provider.name)
                    continue
                except QwenAPIError as exc:
                    errors.append(f"{provider.name}:{exc.status}")
                    if has_next or exc.retryable:
                        logger.warning(
                            "Provider %s failed (status=%s), trying next",
                            provider.name,
                            exc.status,
                        )
                        continue
                    raise

        raise RateLimitError(
            f"All providers failed: {', '.join(errors)}",
            status=429,
            retryable=True,
        )

    async def close(self) -> None:
        for p in self._providers.values():
            session = getattr(p, "_session", None)
            if session:
                await session.aclose()
                p._session = None


llm_client = LLMClient()

# Backward-compatible alias used across codebase
qwen_client = llm_client

__all__ = [
    "LLMClient",
    "QwenAPIError",
    "RateLimitError",
    "LLMClient",
    "llm_client",
    "qwen_client",
    "parse_retry_after_seconds",
    "AGENT_MODELS",
]
