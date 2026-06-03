"""Unified Manus-style progress messages for Telegram HTML."""

from __future__ import annotations

_AGENT_LABELS: dict[str, str] = {
    "orchestrator": "Егор",
    "personal_assistant": "Эльза",
    "coder": "Руслан",
    "research": "Ульяна",
    "security_ai": "Артём",
    "business_manager": "Максим",
    "marketing": "Дарья",
}


def agent_display_name(agent_key: str) -> str:
    return _AGENT_LABELS.get(agent_key, agent_key)


def format_plan_header(steps: list[str]) -> str:
    lines = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
    return f"<b>План:</b>\n{lines}"


def format_step_progress(current: int, total: int, agent_key: str) -> str:
    name = agent_display_name(agent_key)
    return f"📋 <b>Шаг {current}/{total}:</b> {name} работает…"


def format_step_done(current: int, total: int) -> str:
    return f"✅ Шаг {current}/{total} готов."


def cancel_keyboard(task_id: str) -> dict:
    """Inline keyboard to cancel a running plan task."""
    return {
        "inline_keyboard": [
            [{"text": "⏹ Отменить", "callback_data": f"plan_cancel:{task_id}"}]
        ]
    }


def format_handoff(*, from_agent: str, to_agent: str, instruction: str) -> str:
    """User-visible delegation handoff line."""
    src = agent_display_name(from_agent)
    dst = agent_display_name(to_agent)
    preview = (instruction or "").strip()[:120]
    if len((instruction or "").strip()) > 120:
        preview += "…"
    return f"↪️ <b>{src}</b> передаю <b>{dst}</b>: {preview}"


def strip_supervisor_json_leak(text: str) -> str:
    """Hide raw supervisor JSON from user-visible replies."""
    t = (text or "").strip()
    if t.startswith("{") and '"action_type"' in t:
        return "Продолжаю по плану…"
    return text
