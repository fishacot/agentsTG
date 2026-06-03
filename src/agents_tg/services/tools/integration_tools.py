"""Anchor integrations exposed as agent tools."""

from __future__ import annotations

from typing import Any

from src.agents_tg.services.integrations.calendar import create_calendar_event
from src.agents_tg.services.integrations.github import list_github_issues
from src.agents_tg.services.tools.builtin import AgentTool, tool_result


def _uid(kwargs: dict[str, Any]) -> str:
    return str(kwargs.get("user_id") or kwargs.get("telegram_user_id") or "")


def calendar_create_event_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = _uid(kwargs)
        title = str(kwargs.get("title") or "").strip()
        if not uid or not title:
            return tool_result(ok=False, error="missing_title")
        data = await create_calendar_event(
            user_id=uid,
            title=title,
            start_at=kwargs.get("start_at"),
            duration_minutes=int(kwargs.get("duration_minutes") or 60),
        )
        return tool_result(**data)

    return AgentTool(
        name="calendar_create_event",
        description="Создать событие в календаре (CalDAV или stub).",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_at": {
                    "type": "string",
                    "description": "ISO datetime, например 2026-06-02T15:00:00+03:00",
                },
                "duration_minutes": {"type": "integer"},
            },
            "required": ["title"],
        },
        handler=handler,
    )


def github_list_issues_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = _uid(kwargs)
        repo = str(kwargs.get("repo") or "").strip()
        if not uid or not repo:
            return tool_result(ok=False, error="missing_repo")
        data = await list_github_issues(
            user_id=uid,
            repo=repo,
            state=str(kwargs.get("state") or "open"),
            limit=int(kwargs.get("limit") or 10),
        )
        return tool_result(**data)

    return AgentTool(
        name="github_list_issues",
        description="Список открытых issues в GitHub repo (owner/name).",
        parameters={
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "state": {"type": "string", "enum": ["open", "closed", "all"]},
                "limit": {"type": "integer"},
            },
            "required": ["repo"],
        },
        handler=handler,
    )


def staff_summary_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        from src.agents_tg.services.orchestrator_brief import build_staff_summary

        uid = _uid(kwargs)
        if not uid:
            return tool_result(ok=False, error="missing_user")
        data = await build_staff_summary(telegram_user_id=int(uid))
        return tool_result(**data)

    return AgentTool(
        name="staff_summary",
        description="Сводка активных задач и планов штаба для владельца.",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )
