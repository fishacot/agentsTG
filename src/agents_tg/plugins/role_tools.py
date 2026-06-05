"""Role-specific P0 tools per qwen spec."""

from __future__ import annotations

from typing import Any

from src.agents_tg.sandbox.browser_tools import browser_navigate, browser_snapshot
from src.agents_tg.sandbox.docker_runner import run_code
from src.agents_tg.services.agent_runner import AgentTool, tool_result
from src.agents_tg.services.plan_executor import plan_executor


def delegate_task_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        uid = int(str(kwargs.get("user_id", "0")))
        title = str(kwargs.get("title", "Task")).strip()
        plan_raw = kwargs.get("plan") or []
        plan = [str(p) for p in plan_raw] if isinstance(plan_raw, list) else []
        if not uid or not plan:
            return tool_result(ok=False, error="missing plan or user_id")
        from src.agents_tg.services.orchestrator_delegate import _guess_agent_for_step

        steps = [(_guess_agent_for_step(p), p) for p in plan]
        task = await plan_executor.create_task(
            telegram_user_id=uid,
            title=title,
            steps=steps,
        )
        return tool_result(ok=True, task_id=task.task_id, steps=len(task.steps))

    return AgentTool(
        name="delegate_task",
        description="Создать задачу с планом шагов для исполнения специалистами.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "plan": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["plan"],
        },
        handler=handler,
    )


def track_progress_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        task_id = str(kwargs.get("task_id", ""))
        if not task_id:
            return tool_result(ok=False, error="missing task_id")
        steps = await plan_executor._get_steps(task_id)
        return tool_result(ok=True, steps=steps)

    return AgentTool(
        name="track_progress",
        description="Получить статус шагов плана по task_id.",
        parameters={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
        handler=handler,
    )


def merge_results_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        results = kwargs.get("results") or []
        if not isinstance(results, list):
            results = [str(results)]
        merged = "\n\n---\n\n".join(str(r) for r in results)
        return tool_result(ok=True, merged=merged[:4000])

    return AgentTool(
        name="merge_results",
        description="Объединить результаты шагов плана в один ответ.",
        parameters={
            "type": "object",
            "properties": {
                "results": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=handler,
    )


def run_code_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        from src.agents_tg.services.confirmation_service import confirmation_service

        uid = int(str(kwargs.get("user_id") or kwargs.get("telegram_user_id") or 0))
        code = str(kwargs.get("code", ""))
        action = "run_code"
        if confirmation_service.requires_confirmation(action):
            if kwargs.get("confirmed") is not True:
                entry = await confirmation_service.register_and_persist(
                    telegram_user_id=uid,
                    action=action,
                    payload={"code": code[:4000], "timeout_sec": 30},
                )
                return tool_result(
                    ok=False,
                    needs_confirmation=True,
                    action=action,
                    confirmation_token=entry.token,
                    inline_keyboard=confirmation_service.inline_keyboard(entry.token),
                    hint=confirmation_service.hint_for_action(action),
                )
        result = await run_code(code, timeout_sec=30)
        return tool_result(**result)

    return AgentTool(
        name="run_code",
        description="Выполнить Python-код в sandbox (без сети, timeout 30s).",
        parameters={
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
        handler=handler,
    )


def lint_test_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        code = str(kwargs.get("code", ""))
        if not code.strip():
            return tool_result(ok=False, error="empty code")
        issues = []
        if "TODO" in code:
            issues.append("contains TODO")
        if len(code.splitlines()) > 200:
            issues.append("file too long")
        return tool_result(ok=len(issues) == 0, issues=issues)

    return AgentTool(
        name="lint_test",
        description="Базовая проверка кода перед run_code.",
        parameters={
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
        handler=handler,
    )


def browser_navigate_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        url = str(kwargs.get("url", ""))
        data = await browser_navigate(url)
        return tool_result(**data)

    return AgentTool(
        name="browser_navigate",
        description="Открыть URL и получить текст страницы (httpx stub).",
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        handler=handler,
    )


def browser_snapshot_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        url = str(kwargs.get("url", ""))
        data = await browser_snapshot(url)
        return tool_result(**data)

    return AgentTool(
        name="browser_snapshot",
        description="Снимок содержимого страницы по URL.",
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        handler=handler,
    )


def scan_prompt_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        from src.agents_tg.gateway.hooks.injection_guard import _INJECTION_PATTERNS

        text = str(kwargs.get("text", ""))
        hits = [p.pattern for p in _INJECTION_PATTERNS if p.search(text)]
        return tool_result(ok=len(hits) == 0, threats=hits)

    return AgentTool(
        name="scan_prompt",
        description="Проверить текст на injection-паттерны.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        handler=handler,
    )


def list_agent_workspace_tool() -> AgentTool:
    async def handler(**kwargs: Any) -> str:
        from src.agents_tg.services.workspace_memory import list_agent_workspace

        uid = int(str(kwargs.get("user_id", "0")))
        role = str(kwargs.get("agent_key", kwargs.get("role", "personal_assistant")))
        files = list_agent_workspace(uid, role)
        return tool_result(ok=True, files=files)

    return AgentTool(
        name="list_agent_workspace",
        description="Список файлов workspace/users/{id}/agents/{role}/.",
        parameters={
            "type": "object",
            "properties": {"role": {"type": "string"}},
        },
        handler=handler,
    )


def role_tools_for_agent(agent_key: str) -> list[AgentTool]:
    """Return P0 role tools for agent_key."""
    from src.agents_tg.services.tools.integration_tools import (
        calendar_create_event_tool,
        github_list_issues_tool,
        staff_summary_tool,
    )

    mapping: dict[str, list] = {
        "orchestrator": [
            delegate_task_tool,
            track_progress_tool,
            merge_results_tool,
            staff_summary_tool,
        ],
        "personal_assistant": [calendar_create_event_tool],
        "coder": [run_code_tool, lint_test_tool, github_list_issues_tool],
        "research": [browser_navigate_tool, browser_snapshot_tool],
        "security_ai": [scan_prompt_tool],
    }
    builders = mapping.get(agent_key, [])
    tools = [b() for b in builders]
    if agent_key in ("orchestrator", "personal_assistant", "coder", "research"):
        tools.append(list_agent_workspace_tool())
    return tools


def register_role_tools() -> None:
    from src.agents_tg.plugins.registry import plugin_registry

    for key in ("orchestrator", "coder", "research", "security_ai"):
        for tool in role_tools_for_agent(key):
            plugin_registry.register_tool(tool, plugin_id=f"role_{key}")
