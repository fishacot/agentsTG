"""Bind orchestrator plans to shared project context."""

from __future__ import annotations

import re

from src.agents_tg.services.shared_context import shared_context

_PROJECT_MARKERS = ("сайт", "проект", "mvp", "приложен", "landing", "стартап", "бот")


def extract_project_title(message: str, plan: list[str]) -> str:
    patterns = (
        r"(?:сайт|проект|landing|mvp)\s+(?:о|про|на|для)?\s*([^.!?\n]{3,80})",
        r"делаем\s+([^.!?\n]{3,80})",
    )
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            if len(title) > 5:
                return title[:120]
    if plan:
        return plan[0][:120]
    snippet = message.strip()[:80]
    return snippet or "Новый проект"


async def maybe_bind_plan_to_project(
    user_id: str,
    message: str,
    plan: list[str],
) -> None:
    """Create/update active project when multi-step or project-like request."""
    if not user_id.isdigit() or not plan:
        return
    uid = int(user_id)
    low = message.lower()
    should = len(plan) >= 2 or any(m in low for m in _PROJECT_MARKERS)
    if not should:
        return

    title = extract_project_title(message, plan)
    existing = await shared_context.get_active_project(uid)
    if existing and existing.get("title", "").lower() == title.lower():
        project_id = existing["id"]
    else:
        created = await shared_context.set_active_project(
            uid,
            title=title,
            description=message[:500],
        )
        project_id = created["id"]

    steps = "; ".join(plan[:4])
    await shared_context.log_activity(
        uid,
        agent_key="orchestrator",
        summary=f"План ({len(plan)} шагов): {steps}",
        kind="delegation",
        project_id=project_id,
    )
