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


def strip_supervisor_json_leak(text: str) -> str:
    """Hide raw supervisor JSON from user-visible replies."""
    t = (text or "").strip()
    if t.startswith("{") and '"action_type"' in t:
        return "Продолжаю по плану…"
    return text
