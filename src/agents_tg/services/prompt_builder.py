"""Backward-compatible re-exports from services.prompts."""

from src.agents_tg.services.prompts import (
    PromptTier,
    build_memory_block,
    build_system_prompt,
    detect_prompt_tier,
    light_goal_directive,
    tools_for_tier,
    trim_env_block,
    trim_history_block,
    trim_soul,
)

__all__ = [
    "PromptTier",
    "build_memory_block",
    "build_system_prompt",
    "detect_prompt_tier",
    "light_goal_directive",
    "tools_for_tier",
    "trim_env_block",
    "trim_history_block",
    "trim_soul",
]
