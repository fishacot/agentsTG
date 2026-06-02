"""Central registry of tool names exposed per agent role."""

from __future__ import annotations


def tool_names_for_agent(agent_key: str) -> list[str]:
    """Tool names listed in environment context and agent dispatch."""
    common = [
        "remember_about_user",
        "log_project_activity",
        "update_project_status",
        "list_agent_workspace",
    ]
    if agent_key == "personal_assistant":
        return [
            "create_obsidian_note",
            "post_to_notes_channel",
            "add_task",
            "list_tasks",
            "schedule_reminder",
            "send_telegram_message",
            "update_user_profile",
            "set_active_project",
            *common,
        ]
    if agent_key == "orchestrator":
        return [
            "delegation",
            "delegate_task",
            "track_progress",
            "merge_results",
            "send_telegram_message",
            "update_user_profile",
            "set_active_project",
            *common,
        ]
    if agent_key == "coder":
        return ["run_code", "lint_test", "send_telegram_message", *common]
    if agent_key == "research":
        return [
            "browser_navigate",
            "browser_snapshot",
            "deep_research",
            "send_telegram_message",
            *common,
        ]
    if agent_key == "security_ai":
        return ["scan_prompt", "send_telegram_message", *common]
    return ["deep_research", "send_telegram_message", *common]
