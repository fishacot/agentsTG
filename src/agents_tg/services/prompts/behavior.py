"""Backward-compatible re-exports — prefer importing from submodules."""

from src.agents_tg.services.prompts.finalize_directives import (
    FINALIZE_USER_REPLY,
    build_finalize_prompt,
)
from src.agents_tg.services.prompts.orchestrator_directives import (
    ORCHESTRATOR_DIRECT_REPLY_HTML,
    ORCHESTRATOR_JSON_DIRECTIVE,
    REPLAN_DIRECTIVE,
)
from src.agents_tg.services.prompts.styles.personal_assistant import MANUS_PA_STYLE
from src.agents_tg.services.prompts.styles.specialist import (
    MANUS_SPECIALIST_STYLE,
    WEB_TOOL_HINT,
)
from src.agents_tg.services.prompts.system_directives import (
    GOAL_DIRECTIVE,
    TELEGRAM_AGENT_PROTOCOL,
    TELEGRAM_HTML_FORMAT,
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
