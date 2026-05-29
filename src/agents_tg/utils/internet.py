"""Internet search and web fetching tools for agents."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx
import trafilatura
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 25.0
_MAX_RETRIES = 2


async def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web using DuckDuckGo (free)."""
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=max_results)]
                return results
        except Exception as e:
            last_error = e
            logger.warning(
                "Web search attempt %s failed: %s", attempt + 1, e
            )
            await asyncio.sleep(1.0 * (attempt + 1))
    logger.error("Web search error: %s", last_error)
    return []


def _extract_with_trafilatura(downloaded: str) -> str:
    content = trafilatura.extract(
        downloaded,
        include_links=True,
        include_images=False,
        output_format="markdown",
    )
    return content or ""


def _extract_fallback_html(downloaded: str) -> str:
    """Minimal fallback when trafilatura returns empty."""
    try:
        from trafilatura.metadata import extract_metadata

        meta = extract_metadata(downloaded)
        if meta and meta.description:
            return meta.description
    except Exception:
        pass
    text = re.sub(r"<script[^>]*>.*?</script>", "", downloaded, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text[:4000]


async def fetch_web_page(url: str) -> str:
    """Fetch and extract main content from a web page."""
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = _extract_with_trafilatura(downloaded)
                if not content or len(content.strip()) < 80:
                    content = _extract_fallback_html(downloaded)
                if content:
                    return content
                return "Could not extract content from this page."
            async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                content = _extract_with_trafilatura(resp.text)
                if not content:
                    content = _extract_fallback_html(resp.text)
                return content or "Could not extract content from this page."
        except Exception as e:
            last_error = e
            logger.warning("Fetch attempt %s for %s failed: %s", attempt + 1, url, e)
            await asyncio.sleep(1.0 * (attempt + 1))
    logger.error("Web fetch error for %s: %s", url, last_error)
    return f"Error fetching page: {last_error}"


async def fetch_multiple_pages(urls: list[str], max_pages: int = 3) -> list[dict[str, Any]]:
    """Fetch up to max_pages URLs concurrently."""
    selected = urls[:max_pages]
    tasks = [fetch_web_page(u) for u in selected]
    contents = await asyncio.gather(*tasks, return_exceptions=True)
    out: list[dict[str, Any]] = []
    for url, result in zip(selected, contents):
        if isinstance(result, Exception):
            out.append({"url": url, "ok": False, "error": str(result)})
        else:
            out.append({"url": url, "ok": True, "content": str(result)[:3500]})
    return out
