"""Parse supervisor LLM output (JSON routing or HTML fallback)."""

from __future__ import annotations

import json
from typing import Any


def parse_supervisor_response(raw: str) -> dict[str, Any]:
    """Parse JSON routing or fallback to direct HTML reply."""
    clean = (raw or "").strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif clean.startswith("```"):
        parts = clean.split("```")
        if len(parts) >= 2:
            clean = parts[1].strip()

    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    if clean and not clean.lstrip().startswith("{"):
        return {
            "next_agent": "end",
            "direct_reply": clean,
            "plan": [],
            "thought": "plain_text_fallback",
        }
    raise ValueError(f"Invalid supervisor JSON: {raw[:200]}")
