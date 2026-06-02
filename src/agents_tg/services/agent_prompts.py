"""Backward-compatible re-exports from services.prompts.behavior."""

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

__all__ = [
    "FINALIZE_USER_REPLY",
    "GOAL_DIRECTIVE",
    "MANUS_PA_STYLE",
    "MANUS_SPECIALIST_STYLE",
    "ORCHESTRATOR_DIRECT_REPLY_HTML",
    "ORCHESTRATOR_JSON_DIRECTIVE",
    "REPLAN_DIRECTIVE",
    "TELEGRAM_AGENT_PROTOCOL",
    "TELEGRAM_HTML_FORMAT",
    "WEB_TOOL_HINT",
    "build_finalize_prompt",
]
