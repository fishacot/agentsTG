"""Manus-style verify-lite pass after plan steps (heuristics, no separate agent)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_ERROR_MARKERS = (
    '"ok": false',
    '"ok":"false"',
    "'ok': false",
    "tool error",
    "ошибка",
    "failed",
    "traceback",
)
_JSON_SUPERVISOR = re.compile(r'^\s*\{[\s\S]*"action_type"', re.MULTILINE)


@dataclass(frozen=True)
class VerifyStepResult:
    ok: bool
    issues: str = ""
    suggest_replan: bool = False


def _looks_like_tool_failure(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _ERROR_MARKERS)


async def verify_step_result(
    *,
    instruction: str,
    step_summary: str | None,
    agent_key: str,
    tool_results: list[dict[str, Any]] | None = None,
) -> VerifyStepResult:
    """Check step output before marking done; skip LLM to save tokens."""
    _ = instruction, agent_key
    summary = (step_summary or "").strip()
    if _JSON_SUPERVISOR.search(summary):
        return VerifyStepResult(
            ok=False,
            issues="supervisor JSON leaked to user channel",
            suggest_replan=True,
        )
    if not summary:
        return VerifyStepResult(
            ok=False,
            issues="empty step output",
            suggest_replan=True,
        )
    if _looks_like_tool_failure(summary):
        return VerifyStepResult(
            ok=False,
            issues="step output indicates tool failure",
            suggest_replan=True,
        )
    if tool_results:
        for tr in tool_results:
            if isinstance(tr, dict) and tr.get("ok") is False:
                return VerifyStepResult(
                    ok=False,
                    issues="structured tool result not ok",
                    suggest_replan=True,
                )
            raw = tr if isinstance(tr, str) else json.dumps(tr, ensure_ascii=False)
            if _looks_like_tool_failure(raw):
                return VerifyStepResult(
                    ok=False,
                    issues="tool result contains error markers",
                    suggest_replan=True,
                )
    if len(summary) < 12 and "привет" not in summary.lower():
        return VerifyStepResult(
            ok=False,
            issues="response unusually short",
            suggest_replan=False,
        )
    return VerifyStepResult(ok=True)
