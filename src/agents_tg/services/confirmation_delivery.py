"""Parse tool JSON and surface confirmation UI to outbound sink."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConfirmationUI:
    text: str
    reply_markup: dict[str, Any]


def parse_confirmation_from_tool_output(tool_output: str) -> ConfirmationUI | None:
    try:
        data = json.loads(tool_output)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not data.get("needs_confirmation"):
        return None
    hint = str(data.get("hint") or "Требуется подтверждение.")
    markup = data.get("inline_keyboard")
    if not isinstance(markup, dict):
        return None
    return ConfirmationUI(text=hint, reply_markup=markup)
