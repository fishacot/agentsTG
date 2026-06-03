"""In-process cancel flags for long-running plan tasks."""

from __future__ import annotations

_cancelled: set[str] = set()


def request_cancel(task_id: str) -> None:
    _cancelled.add(task_id)


def is_cancelled(task_id: str) -> bool:
    return task_id in _cancelled


def clear_cancel(task_id: str) -> None:
    _cancelled.discard(task_id)
