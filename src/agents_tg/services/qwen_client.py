"""Backward-compatible re-export — use llm_client."""

from src.agents_tg.services.agent_models import AGENT_MODELS
from src.agents_tg.services.llm_client import (
    LLMClient,
    QwenAPIError,
    RateLimitError,
    parse_retry_after_seconds,
    qwen_client,
)

__all__ = [
    "QwenClient",
    "QwenAPIError",
    "RateLimitError",
    "qwen_client",
    "AGENT_MODELS",
    "parse_retry_after_seconds",
]

# Legacy class name alias
QwenClient = LLMClient
