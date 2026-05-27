"""Hugging Face Inference API client (OpenAI-compatible chat completions)."""

import logging
from typing import Any

import httpx

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_models import AGENT_MODELS, MODEL_DEFAULT

logger = logging.getLogger(__name__)
settings = get_settings()


class QwenClient:
    """Async client for Hugging Face chat models (same token for all agents)."""

    def __init__(self) -> None:
        self.api_key = settings.QWEN_API_KEY
        self.api_base = settings.QWEN_API_BASE
        self.default_model = settings.QWEN_MODEL or MODEL_DEFAULT
        self._session: httpx.AsyncClient | None = None

    def model_for_agent(self, agent_key: str) -> str:
        """Return HF model id for an agent (env overrides supported in settings)."""
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
        """
        Send chat request to Hugging Face Inference API.

        Args:
            messages: OpenAI-style message dicts with role and content
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Explicit HF model id (highest priority)
            agent_key: Agent key to resolve model from AGENT_MODELS
        """
        resolved_model = model or (
            self.model_for_agent(agent_key) if agent_key else self.default_model
        )
        session = await self._get_session()

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await session.post(self.api_base, json=payload)
            response.raise_for_status()
            result = response.json()
            return self._extract_text(result)

        except httpx.HTTPStatusError as e:
            logger.error(
                "HF API error model=%s status=%s body=%s",
                resolved_model,
                e.response.status_code,
                e.response.text[:500],
            )
            raise QwenAPIError(
                f"API error ({resolved_model}): {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error("HF request failed model=%s: %s", resolved_model, e)
            raise QwenAPIError(f"Request failed: {e}") from e

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
    """Exception for Hugging Face inference API errors."""

    pass


qwen_client = QwenClient()

# Re-export for convenience
__all__ = ["QwenClient", "QwenAPIError", "qwen_client", "AGENT_MODELS"]
