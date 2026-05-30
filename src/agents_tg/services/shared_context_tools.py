"""LLM tools for shared user profile and project focus."""

from __future__ import annotations

from typing import Any

from src.agents_tg.services.agent_runner import AgentTool, tool_result
from src.agents_tg.services.shared_context import shared_context
from src.agents_tg.services.workspace_memory import (
    append_daily_log,
    write_user_md,
)


def _uid(kwargs: dict[str, Any]) -> int:
    raw = str(kwargs.get("user_id", "0"))
    return int(raw) if raw.isdigit() else 0


def update_user_profile_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = _uid(kwargs)
        if not uid:
            return tool_result(ok=False, error="invalid_user_id")
        likes = kwargs.get("likes")
        dislikes = kwargs.get("dislikes")
        profile = await shared_context.update_profile(
            uid,
            display_name=kwargs.get("display_name"),
            address_as=kwargs.get("address_as"),
            bio=kwargs.get("bio"),
            likes=list(likes) if isinstance(likes, list) else None,
            dislikes=list(dislikes) if isinstance(dislikes, list) else None,
            style=kwargs.get("style"),
        )
        write_user_md(
            uid,
            display_name=profile.get("display_name"),
            address_as=profile.get("address_as"),
            bio=profile.get("bio"),
            preferences=profile.get("preferences"),
        )
        return tool_result(ok=True, profile=profile)

    return AgentTool(
        name="update_user_profile",
        description=(
            "Обновить профиль пользователя (имя, как обращаться, bio, likes/dislikes, стиль). "
            "Видят все 7 агентов."
        ),
        parameters={
            "type": "object",
            "properties": {
                "display_name": {"type": "string"},
                "address_as": {"type": "string", "description": "Как обращаться"},
                "bio": {"type": "string"},
                "likes": {"type": "array", "items": {"type": "string"}},
                "dislikes": {"type": "array", "items": {"type": "string"}},
                "style": {"type": "string", "description": "Стиль общения"},
            },
        },
        handler=handler,
    )


def set_active_project_tool(agent_key: str) -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = _uid(kwargs)
        title = str(kwargs.get("title", "")).strip()
        if not uid or not title:
            return tool_result(ok=False, error="missing_title_or_user")
        project = await shared_context.set_active_project(
            uid,
            title=title,
            description=str(kwargs.get("description", "") or "") or None,
        )
        append_daily_log(uid, agent_key=agent_key, text=f"Новый проект: {title}")
        return tool_result(ok=True, project=project)

    return AgentTool(
        name="set_active_project",
        description=(
            "Создать или переключить активный проект (общий фокус для всех агентов). "
            "Предыдущий active → paused."
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Название проекта"},
                "description": {"type": "string"},
            },
            "required": ["title"],
        },
        handler=handler,
    )


def update_project_status_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = _uid(kwargs)
        status = str(kwargs.get("status", "")).strip()
        if not uid or not status:
            return tool_result(ok=False, error="missing_status")
        result = await shared_context.update_project_status(
            uid,
            project_id=kwargs.get("project_id"),
            status=status,
        )
        return tool_result(**result)

    return AgentTool(
        name="update_project_status",
        description="Изменить статус проекта: active, paused, done.",
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "done"],
                },
                "project_id": {"type": "integer"},
            },
            "required": ["status"],
        },
        handler=handler,
    )


def log_project_activity_tool(agent_key: str) -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = _uid(kwargs)
        summary = str(kwargs.get("summary", "")).strip()
        kind = str(kwargs.get("kind", "note"))
        if not uid or not summary:
            return tool_result(ok=False, error="empty_summary")
        result = await shared_context.log_activity(
            uid,
            agent_key=agent_key,
            summary=summary,
            kind=kind,
            project_id=kwargs.get("project_id"),
        )
        if result.get("ok"):
            append_daily_log(uid, agent_key=agent_key, text=summary)
        return tool_result(**result)

    return AgentTool(
        name="log_project_activity",
        description=(
            "Записать в журнал активного проекта что сделано (видят все агенты, "
            "в т.ч. Эльза в ЛС)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "1–2 предложения"},
                "kind": {
                    "type": "string",
                    "enum": [
                        "research",
                        "code",
                        "plan",
                        "note",
                        "delegation",
                        "marketing",
                        "security",
                    ],
                },
            },
            "required": ["summary"],
        },
        handler=handler,
    )


def shared_context_tools(*, agent_key: str) -> list[AgentTool]:
    tools = [
        log_project_activity_tool(agent_key),
        update_project_status_tool(),
    ]
    if agent_key in ("orchestrator", "personal_assistant"):
        tools.extend(
            [update_user_profile_tool(), set_active_project_tool(agent_key)]
        )
    return tools
