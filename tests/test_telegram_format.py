"""Tests for Telegram HTML formatting."""

from src.agents_tg.utils.telegram_format import (
    escape_html,
    sanitize_html_for_telegram,
)


def test_escape_html_special_chars() -> None:
    assert escape_html("a & b < c") == "a &amp; b &lt; c"


def test_sanitize_plain_text() -> None:
    result = sanitize_html_for_telegram("Hello & world")
    assert "&amp;" in result
    assert "<" not in result.replace("&lt;", "")


def test_sanitize_keeps_allowed_tags() -> None:
    raw = "<b>Title</b> and <code>x</code>"
    result = sanitize_html_for_telegram(raw)
    assert "<b>Title</b>" in result
    assert "<code>x</code>" in result


def test_markdown_bold_converted() -> None:
    result = sanitize_html_for_telegram("**bold** text")
    assert "<b>bold</b>" in result
