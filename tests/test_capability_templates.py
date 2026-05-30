"""Tests for static capability templates."""

from src.agents_tg.services.capability_templates import build_elza_capabilities_html
from src.agents_tg.services.prompt_builder import is_capabilities_question


def test_elza_capabilities_html():
    html = build_elza_capabilities_html()
    assert "<b>Я Эльза</b>" in html
    assert "Заметки" in html
    assert "@ruslan_coder_bot" in html


def test_capabilities_question_russian():
    assert is_capabilities_question("чем ты можешь помочь")
