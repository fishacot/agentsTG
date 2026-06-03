"""Per-user buffer of structured tool results for plan verify (Manus wave 2)."""

from __future__ import annotations

from typing import Any

_buffer: dict[str, list[dict[str, Any]]] = {}


def record(user_id: str, tool_name: str, result: Any) -> None:
    key = str(user_id)
    if key not in _buffer:
        _buffer[key] = []
    payload = result if isinstance(result, dict) else {"raw": result}
    _buffer[key].append({"tool": tool_name, "result": payload})


def drain(user_id: str) -> list[dict[str, Any]]:
    key = str(user_id)
    items = _buffer.pop(key, [])
    return list(items)


def peek(user_id: str) -> list[dict[str, Any]]:
    return list(_buffer.get(str(user_id), []))
