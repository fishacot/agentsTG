"""Qwen API client for HuggingFace Inference API."""

import logging

import httpx

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class QwenClient:
    """Client for Qwen model via HuggingFace Inference API."""

    def __init__(self) -> None:
        self.api_key = settings.QWEN_API_KEY
        self.model = settings.QWEN_MODEL
        self.api_base = settings.QWEN_API_BASE
        self._session: httpx.AsyncClient | None = None

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._session

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """
        Send chat request to Qwen model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        session = await self._get_session()

        payload = {
            "inputs": {
                "messages": messages,
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        try:
            response = await session.post(
                f"{self.api_base}",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            # Parse the response based on API format
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "") or result[0].get("text", "")
            return str(result)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise QwenAPIError(f"API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise QwenAPIError(f"Request failed: {e}") from e

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None


class QwenAPIError(Exception):
    """Exception for Qwen API errors."""

    pass


# Singleton instance
qwen_client = QwenClient()
