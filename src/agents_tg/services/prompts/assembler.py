"""Orchestrate tiered system prompt assembly."""

from __future__ import annotations

from src.agents_tg.services.prompts.styles.specialist import WEB_TOOL_HINT
from src.agents_tg.services.prompts.system_directives import (
    GOAL_DIRECTIVE,
    TELEGRAM_AGENT_PROTOCOL,
    TELEGRAM_HTML_FORMAT,
)
from src.agents_tg.services.prompts.tier_rules import (
    RESEARCH_ACTION_PATTERN,
    PromptTier,
    light_goal_directive,
    trim_env_block,
    trim_history_block,
    trim_soul,
)


def build_system_prompt(
    *,
    tier: PromptTier,
    human_name: str,
    designation: str,
    soul: str,
    env_block: str,
    history_block: str,
    memory_block: str,
    playbook_block: str = "",
    output_hints: str,
    include_web_tools: bool,
    user_id: str,
    user_message: str = "",
) -> str:
    goal = light_goal_directive() if tier == PromptTier.LIGHT else GOAL_DIRECTIVE
    protocol = "" if tier == PromptTier.LIGHT else f"\n\n{TELEGRAM_AGENT_PROTOCOL}"
    html_fmt = TELEGRAM_HTML_FORMAT
    show_web = (
        include_web_tools
        and tier == PromptTier.FULL
        and RESEARCH_ACTION_PATTERN.search(user_message or "")
    )
    web_hint = WEB_TOOL_HINT if show_web else ""
    hints = f"\n\n{output_hints}" if output_hints and tier != PromptTier.LIGHT else ""
    playbook = ""
    if playbook_block and tier != PromptTier.LIGHT:
        playbook = f"\n\n{playbook_block.strip()}"

    return (
        f"{goal}{protocol}\n\n{html_fmt}\n\n"
        f"Ты — <b>{human_name}</b>, {designation}.\n\n"
        f"{trim_soul(soul, tier)}"
        f"{trim_env_block(env_block, tier)}"
        f"{trim_history_block(history_block, tier)}"
        f"{memory_block}"
        f"{playbook}"
        f"{web_hint}{hints}\n\n"
        f"user_id для инструментов: {user_id}"
    )
