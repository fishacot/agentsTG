"""Replay gated tool actions after Telegram confirmation."""

from __future__ import annotations

import logging
from typing import Any

from src.agents_tg.services.confirmation_service import PendingConfirmation

logger = logging.getLogger(__name__)


async def replay_confirmed_action(entry: PendingConfirmation) -> dict[str, Any]:
    """Execute stored action with confirmed=True semantics."""
    action = entry.action
    payload = entry.payload or {}
    uid = entry.telegram_user_id

    if action.startswith("update_project_status:"):
        status = str(payload.get("status") or action.split(":", 1)[-1])
        from src.agents_tg.services.shared_context import shared_context
        from src.agents_tg.services.workspace_memory import refresh_memory_md

        result = await shared_context.update_project_status(
            uid,
            project_id=payload.get("project_id"),
            status=status,
        )
        if result.get("ok") and status == "done":
            refresh_memory_md(uid, project_title=None)
        return result

    if action == "run_code" or action.startswith("run_code:"):
        from src.agents_tg.sandbox.docker_runner import run_code

        code = str(payload.get("code") or "")
        if not code:
            return {"ok": False, "error": "missing_code"}
        timeout = int(payload.get("timeout_sec") or 30)
        result = await run_code(code, timeout_sec=timeout)
        return {"ok": True, "result": result}

    logger.warning("No replay handler for action=%s", action)
    return {"ok": False, "error": "unsupported_action"}


def format_replay_message(result: dict[str, Any]) -> str:
    if result.get("ok"):
        return "✅ Действие выполнено."
    return f"❌ Не удалось выполнить: {result.get('error', 'unknown')}"
