"""Tests for orchestrator supervisor JSON parsing."""

from src.agents_tg.services.supervisor_parse import parse_supervisor_response


def test_parse_json_routing():
    raw = '{"next_agent": "end", "direct_reply": "Привет", "plan": []}'
    data = parse_supervisor_response(raw)
    assert data["next_agent"] == "end"
    assert data["direct_reply"] == "Привет"


def test_parse_html_fallback():
    raw = "<b>Привет!</b> Я Егор."
    data = parse_supervisor_response(raw)
    assert data["next_agent"] == "end"
    assert "Егор" in data["direct_reply"]
