"""Per-request LLM context (user id for budget/cooldown)."""

from __future__ import annotations

from contextvars import ContextVar

current_llm_user_id: ContextVar[str] = ContextVar(
    "current_llm_user_id", default="default"
)
current_llm_step_kind: ContextVar[str | None] = ContextVar(
    "current_llm_step_kind", default=None
)


def set_llm_user_id(user_id: str) -> None:
    current_llm_user_id.set(str(user_id))


def get_llm_user_id() -> str:
    return current_llm_user_id.get()


def set_llm_step_kind(step_kind: str | None) -> None:
    current_llm_step_kind.set(step_kind.strip().lower() if step_kind else None)


def get_llm_step_kind() -> str | None:
    return current_llm_step_kind.get()
