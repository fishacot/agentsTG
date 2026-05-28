"""LLM client for Groq / Hugging Face (OpenAI-compatible chat completions)."""

import asyncio
import logging
from typing import Any

import httpx

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_models import AGENT_MODELS, MODEL_DEFAULT

logger = logging.getLogger(__name__)
settings = get_settings()

# Serialize LLM calls to avoid Groq free-tier burst 429 errors
_LLM_SEMAPHORE = asyncio.Semaphore(1)
_RETRYABLE_STATUS = frozenset({429, 503})
_RETRY_DELAYS_SEC = (2.0, 4.0, 8.0)


class QwenClient:
    """Async client for Groq or HF chat models (one API key for all agents)."""

    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.api_base = settings.llm_api_base
        self.default_model = settings.llm_default_model or MODEL_DEFAULT
        self._session: httpx.AsyncClient | None = None

    def model_for_agent(self, agent_key: str) -> str:
        """Return model id for an agent (env overrides supported in settings)."""
        return settings.get_agent_model(agent_key)

    async def _get_session(self) -> httpx.AsyncClient:
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._session

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        model: str | None = None,
        agent_key: str | None = None,
    ) -> str:
        """Send chat request to Groq or Hugging Face Inference API."""
        resolved_model = model or (
            self.model_for_agent(agent_key) if agent_key else self.default_model
        )

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with _LLM_SEMAPHORE:
            return await self._post_with_retry(resolved_model, payload)

    async def _post_with_retry(
        self,
        resolved_model: str,
        payload: dict[str, Any],
    ) -> str:
        session = await self._get_session()
        last_error: Exception | None = None
        max_attempts = len(_RETRY_DELAYS_SEC) + 1

        for attempt in range(max_attempts):
            try:
                response = await session.post(self.api_base, json=payload)
                response.raise_for_status()
                return self._extract_text(response.json())
            except httpx.HTTPStatusError as e:
                last_error = e
                if (
                    e.response.status_code not in _RETRYABLE_STATUS
                    or attempt >= max_attempts - 1
                ):
                    break
                logger.warning(
                    "LLM rate limit model=%s status=%s attempt=%s/%s",
                    resolved_model,
                    e.response.status_code,
                    attempt + 1,
                    max_attempts - 1,
                )
                await asyncio.sleep(_RETRY_DELAYS_SEC[attempt])
            except Exception as e:
                last_error = e
                break

        if isinstance(last_error, httpx.HTTPStatusError):
            logger.error(
                "LLM API error model=%s status=%s body=%s",
                resolved_model,
                last_error.response.status_code,
                last_error.response.text[:500],
            )
            raise QwenAPIError(
                f"API error ({resolved_model}): {last_error.response.status_code}"
            ) from last_error

        logger.error("LLM request failed model=%s: %s", resolved_model, last_error)
        raise QwenAPIError(f"Request failed: {last_error}") from last_error

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Parse OpenAI-compatible or legacy HF inference response."""
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

    async def close(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None


class QwenAPIError(Exception):
    """Exception for LLM inference API errors."""

    pass


qwen_client = QwenClient()

__all__ = ["QwenClient", "QwenAPIError", "qwen_client", "AGENT_MODELS"]
