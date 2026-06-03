"""Staff-wide status brief for orchestrator."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.agents_tg.db.models import AgentTask


async def build_staff_summary(*, telegram_user_id: int) -> dict[str, Any]:
    """Summarize in-flight agent tasks for solo owner."""
    items: list[dict[str, Any]] = []
    from src.agents_tg.services.plan_executor import plan_executor

    factory = plan_executor._factory
    if factory:
        try:
            async with factory() as session:
                result = await session.execute(
                    select(AgentTask)
                    .where(AgentTask.user_id == telegram_user_id)
                    .where(AgentTask.status.in_(("planned", "running")))
                    .order_by(AgentTask.updated_at.desc())
                    .limit(10)
                )
                for row in result.scalars().all():
                    items.append(
                        {
                            "task_id": row.id,
                            "title": row.title,
                            "status": row.status,
                            "agent_key": row.agent_key,
                        }
                    )
        except Exception:
            pass

    if not items:
        for tid, rec in plan_executor._memory_tasks.items():
            if rec.get("user_id") == telegram_user_id and rec.get("status") in (
                "planned",
                "running",
            ):
                items.append(
                    {
                        "task_id": tid,
                        "title": rec.get("title"),
                        "status": rec.get("status"),
                        "agent_key": rec.get("agent_key"),
                    }
                )

    return {
        "ok": True,
        "active_count": len(items),
        "tasks": items,
        "hint": "Используй для ответа «что в работе».",
    }
