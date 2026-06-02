"""Tiered prompt assembly package."""

from src.agents_tg.services.prompts.assembler import build_system_prompt
from src.agents_tg.services.prompts.behavior import (
    FINALIZE_USER_REPLY,
    GOAL_DIRECTIVE,
    MANUS_PA_STYLE,
    MANUS_SPECIALIST_STYLE,
    ORCHESTRATOR_DIRECT_REPLY_HTML,
    ORCHESTRATOR_JSON_DIRECTIVE,
    REPLAN_DIRECTIVE,
    TELEGRAM_AGENT_PROTOCOL,
    TELEGRAM_HTML_FORMAT,
    WEB_TOOL_HINT,
    build_finalize_prompt,
)
from src.agents_tg.services.prompts.proactive import (
    HEARTBEAT_WAKE_PROMPT,
    MORNING_DIGEST_PROMPT,
)
from src.agents_tg.services.prompts.identity import (
    human_name_for,
    load_soul,
    prompt_identity,
    resolve_identity,
    soul_path_for,
    souls_dir,
)
from src.agents_tg.services.prompts.memory_block import (
    build_memory_block,
    build_scheduled_context,
)
from src.agents_tg.services.prompts.tier_rules import (
    PromptTier,
    RESEARCH_ACTION_PATTERN,
    TASK_LIST_PATTERN,
    detect_prompt_tier,
    light_goal_directive,
    tools_for_tier,
    trim_env_block,
    trim_history_block,
    trim_soul,
)

__all__ = [
    "FINALIZE_USER_REPLY",
    "GOAL_DIRECTIVE",
    "HEARTBEAT_WAKE_PROMPT",
    "MANUS_PA_STYLE",
    "MANUS_SPECIALIST_STYLE",
    "MORNING_DIGEST_PROMPT",
    "ORCHESTRATOR_DIRECT_REPLY_HTML",
    "ORCHESTRATOR_JSON_DIRECTIVE",
    "REPLAN_DIRECTIVE",
    "PromptTier",
    "build_finalize_prompt",
    "RESEARCH_ACTION_PATTERN",
    "TASK_LIST_PATTERN",
    "TELEGRAM_AGENT_PROTOCOL",
    "TELEGRAM_HTML_FORMAT",
    "WEB_TOOL_HINT",
    "build_memory_block",
    "build_scheduled_context",
    "build_system_prompt",
    "detect_prompt_tier",
    "human_name_for",
    "light_goal_directive",
    "load_soul",
    "prompt_identity",
    "resolve_identity",
    "soul_path_for",
    "souls_dir",
    "tools_for_tier",
    "trim_env_block",
    "trim_history_block",
    "trim_soul",
]
