"""Tests for gateway block coalescing."""

from src.agents_tg.gateway.coalesce import BlockCoalescer


def test_coalesce_merges_short_blocks_within_idle_window():
    c = BlockCoalescer(idle_ms=400, short_limit=256)
    c.push("Ищу…", 1000)
    c.push("Читаю страницу", 1200)
    assert c.pending == "Ищу…\nЧитаю страницу"
    out = c.flush()
    assert out == ["Ищу…\nЧитаю страницу"]


def test_coalesce_splits_when_idle_exceeded():
    c = BlockCoalescer(idle_ms=400)
    c.push("first", 1000)
    c.push("second", 1500)
    assert c.pending == "second"
    out = c.flush()
    assert out == ["first", "second"]


def test_coalesce_does_not_merge_long_blocks():
    c = BlockCoalescer(idle_ms=500, short_limit=20)
    long_a = "a" * 30
    long_b = "b" * 30
    c.push(long_a, 1000)
    c.push(long_b, 1100)
    out = c.flush()
    assert out == [long_a, long_b]


def test_coalesce_skips_empty_push():
    c = BlockCoalescer(idle_ms=400)
    c.push("  ", 1000)
    c.push("ok", 1100)
    assert c.flush() == ["ok"]


def test_coalesce_preview_text_includes_committed_and_pending():
    c = BlockCoalescer(idle_ms=400)
    c.push("one", 1000)
    c.push("two", 4200)
    assert "one" in c.preview_text
    assert "two" in c.preview_text
    c.flush()
    c.push("a", 5000)
    assert c.preview_text == "a"
