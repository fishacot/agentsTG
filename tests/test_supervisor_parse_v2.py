"""Tests for supervisor JSON v2 parsing."""

from src.agents_tg.services.supervisor_parse import (
    normalize_supervisor_data,
    parse_supervisor_response,
)


def test_v2_delegate():
    data = normalize_supervisor_data(
        {
            "action_type": "delegate",
            "agent_name": "ResearchAgent",
            "task_description": "Найди новости об ИИ",
            "reasoning": "research task",
        }
    )
    assert data["next_agent"] == "research"
    assert data["request_replan"] is False
    assert "Найди" in data["plan"][0]


def test_v2_final_answer():
    data = normalize_supervisor_data(
        {
            "action_type": "final_answer",
            "final_answer": "<b>Привет!</b>",
            "reasoning": "greeting",
        }
    )
    assert data["next_agent"] == "end"
    assert data["direct_reply"] == "<b>Привет!</b>"


def test_v2_direct_reply():
    data = normalize_supervisor_data(
        {
            "action_type": "direct_reply",
            "user_message": "Здравствуйте",
            "reasoning": "small talk",
        }
    )
    assert data["next_agent"] == "end"
    assert data["direct_reply"] == "Здравствуйте"


def test_v2_request_replan():
    data = normalize_supervisor_data(
        {
            "action_type": "request_replan",
            "reasoning": "step failed",
        }
    )
    assert data["request_replan"] is True
    assert data["plan"] == []


def test_legacy_next_agent():
    data = normalize_supervisor_data(
        {
            "next_agent": "coder",
            "direct_reply": "",
            "plan": ["шаг 1"],
            "thought": "code",
        }
    )
    assert data["next_agent"] == "coder"
    assert data["action_type"] == "legacy"


def test_parse_plain_text_fallback():
    data = parse_supervisor_response("Привет! Как дела?")
    assert data["next_agent"] == "end"
    assert "Привет" in data["direct_reply"]
