"""Per-agent delivery and autonomy profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

TELEGRAM_TEXT_LIMIT: Final[int] = 4096


@dataclass(frozen=True)
class AgentDeliveryProfile:
    """How an agent delivers output and runs tool loops."""

    agent_key: str
    max_tokens: int
    max_tool_rounds: int
    text_chunk_limit: int = TELEGRAM_TEXT_LIMIT
    streaming_mode: str = "partial"  # partial | message_end
    autonomy_level: str = "medium"  # low | medium | high


PROFILES: Final[dict[str, AgentDeliveryProfile]] = {
    "orchestrator": AgentDeliveryProfile(
        agent_key="orchestrator",
        max_tokens=640,
        max_tool_rounds=1,
        streaming_mode="partial",
        autonomy_level="low",
    ),
    "personal_assistant": AgentDeliveryProfile(
        agent_key="personal_assistant",
        max_tokens=768,
        max_tool_rounds=3,
        autonomy_level="high",
    ),
    "coder": AgentDeliveryProfile(
        agent_key="coder",
        max_tokens=1536,
        max_tool_rounds=2,
        streaming_mode="message_end",
        autonomy_level="medium",
    ),
    "research": AgentDeliveryProfile(
        agent_key="research",
        max_tokens=768,
        max_tool_rounds=2,
        autonomy_level="high",
    ),
    "security_ai": AgentDeliveryProfile(
        agent_key="security_ai",
        max_tokens=768,
        max_tool_rounds=2,
        autonomy_level="medium",
    ),
    "business_manager": AgentDeliveryProfile(
        agent_key="business_manager",
        max_tokens=768,
        max_tool_rounds=2,
        autonomy_level="medium",
    ),
    "marketing": AgentDeliveryProfile(
        agent_key="marketing",
        max_tokens=768,
        max_tool_rounds=2,
        autonomy_level="medium",
    ),
    "general": AgentDeliveryProfile(
        agent_key="general",
        max_tokens=768,
        max_tool_rounds=2,
        autonomy_level="medium",
    ),
}


def get_delivery_profile(agent_key: str) -> AgentDeliveryProfile:
    return PROFILES.get(agent_key, PROFILES["general"])
