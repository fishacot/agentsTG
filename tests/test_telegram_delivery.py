"""Tests for Telegram delivery chunking."""

from src.agents_tg.channels.telegram_delivery import split_telegram_html


def test_split_short_text_single_chunk():
    text = "Hello world"
    assert split_telegram_html(text) == ["Hello world"]


def test_split_long_text_multiple_chunks():
    text = "a" * 5000
    parts = split_telegram_html(text, limit=4096)
    assert len(parts) >= 2
    assert sum(len(p) for p in parts) >= 5000 - 10


def test_split_preserves_pre_block():
    text = "<pre>" + "x" * 5000 + "</pre>"
    parts = split_telegram_html(text, limit=2000)
    assert len(parts) >= 2
    joined = "".join(parts)
    assert "x" in joined
