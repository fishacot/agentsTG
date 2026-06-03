"""Lightweight structural validation for tool outputs (no jsonschema dep)."""

from __future__ import annotations

from typing import Any


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def validate_tool_output(tool_name: str, data: Any) -> tuple[bool, str]:
    """Return (ok, reason). Formal check before heuristic verify."""
    if not _is_dict(data):
        return False, "tool_output_not_object"

    if tool_name in ("browser_navigate", "browser_snapshot"):
        if data.get("ok") is True:
            code = data.get("status_code")
            if code is None:
                return False, "browser_missing_status_code"
            if not isinstance(code, int) or code < 100 or code > 599:
                return False, "browser_invalid_status_code"
        return True, ""

    if tool_name == "deep_research":
        if data.get("ok") is True:
            has_body = bool(
                data.get("results")
                or data.get("summary")
                or data.get("answer")
                or data.get("sources")
            )
            if not has_body:
                return False, "deep_research_empty_body"
        return True, ""

    if tool_name == "run_code":
        if data.get("ok") is True and not data.get("stdout") and not data.get("output"):
            return False, "run_code_empty_output"
        return True, ""

    return True, ""


def validate_tool_results(
    tool_results: list[dict[str, Any]] | None,
) -> tuple[bool, str]:
    """Validate a batch of structured tool results if name present."""
    if not tool_results:
        return True, ""
    for tr in tool_results:
        if not _is_dict(tr):
            continue
        name = str(tr.get("tool") or tr.get("name") or "")
        payload = tr.get("result") if "result" in tr else tr
        if name:
            ok, reason = validate_tool_output(name, payload)
            if not ok:
                return False, reason
        elif tr.get("ok") is False:
            return False, "tool_result_not_ok"
    return True, ""
