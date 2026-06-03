"""Tests for tool output schema validation."""

from src.agents_tg.services.tool_schemas import (
    validate_tool_output,
    validate_tool_results,
)


def test_browser_requires_status_code():
    ok, reason = validate_tool_output("browser_navigate", {"ok": True, "title": "Hi"})
    assert ok is False
    assert reason == "browser_missing_status_code"


def test_deep_research_requires_body():
    ok, reason = validate_tool_output("deep_research", {"ok": True})
    assert ok is False
    assert reason == "deep_research_empty_body"


def test_validate_tool_results_batch():
    ok, reason = validate_tool_results(
        [{"tool": "browser_snapshot", "result": {"ok": True, "status_code": 200}}]
    )
    assert ok is True
    assert reason == ""
