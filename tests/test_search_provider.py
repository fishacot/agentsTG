"""Tests for deep_research search provider."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents_tg.services.search_provider import deep_research


@pytest.mark.asyncio
async def test_deep_research_merges_results() -> None:
    search_rows = [
        {"title": "A", "href": "https://a.com", "body": "snippet a"},
        {"title": "B", "href": "https://b.com", "body": "snippet b"},
    ]
    pages = [
        {"url": "https://a.com", "ok": True, "content": "Full content A"},
    ]

    with (
        patch(
            "src.agents_tg.services.search_provider.web_search",
            new=AsyncMock(return_value=search_rows),
        ),
        patch(
            "src.agents_tg.services.search_provider.fetch_multiple_pages",
            new=AsyncMock(return_value=pages),
        ),
    ):
        result = await deep_research("test query")

    assert result["ok"] is True
    assert result["source_count"] == 2
    assert "Full content A" in result["context"]
    assert "https://a.com" in result["context"]
