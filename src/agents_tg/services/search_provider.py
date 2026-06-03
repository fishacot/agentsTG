"""Deep web research chain: DDG search + page extraction (budget $0)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from src.agents_tg.utils.internet import fetch_multiple_pages, web_search

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 8000


def _normalize_url(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.netloc}{p.path}".lower().rstrip("/")
    except Exception:
        return url


async def deep_research(
    query: str,
    *,
    max_results: int = 5,
    max_pages: int = 3,
    extra_queries: list[str] | None = None,
) -> dict[str, Any]:
    """
    Search DDG, fetch top pages, merge deduplicated context for LLM.
    """
    queries = [query.strip()]
    if extra_queries:
        for q in extra_queries[:2]:
            q = q.strip()
            if q and q not in queries:
                queries.append(q)

    all_snippets: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for q in queries:
        rows = await web_search(q, max_results=max_results)
        for row in rows:
            href = row.get("href") or row.get("url") or ""
            norm = _normalize_url(href)
            if norm in seen_urls:
                continue
            seen_urls.add(norm)
            all_snippets.append(
                {
                    "title": row.get("title") or "",
                    "url": href,
                    "snippet": (row.get("body") or "")[:400],
                    "query": q,
                }
            )

    urls = [s["url"] for s in all_snippets if s.get("url")][: max_pages + 2]
    pages = await fetch_multiple_pages(urls, max_pages=max_pages)

    page_by_url = {p["url"]: p for p in pages}
    merged_parts: list[str] = []
    total = 0

    for snip in all_snippets:
        block_lines = [
            f"### {snip['title']}",
            f"URL: {snip['url']}",
            f"Snippet: {snip['snippet']}",
        ]
        page = page_by_url.get(snip["url"])
        if page and page.get("ok") and page.get("content"):
            excerpt = str(page["content"])[:2500]
            block_lines.append(f"Content excerpt:\n{excerpt}")
        block = "\n".join(block_lines)
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        merged_parts.append(block)
        total += len(block)

    citations = format_research_citations(all_snippets[:10])
    return {
        "ok": True,
        "queries": queries,
        "sources": all_snippets[:10],
        "citations": citations,
        "pages_fetched": len(pages),
        "context": "\n\n---\n\n".join(merged_parts),
        "source_count": len(all_snippets),
    }


def format_research_citations(
    sources: list[dict[str, str]], *, max_items: int = 5
) -> str:
    """Numbered citation block for LLM/user (Telegram HTML)."""
    lines: list[str] = []
    for i, snip in enumerate(sources[:max_items], start=1):
        title = (snip.get("title") or "Источник").strip()
        url = (snip.get("url") or "").strip()
        if url:
            lines.append(f'{i}. <a href="{url}">{title}</a>')
        else:
            lines.append(f"{i}. {title}")
    return "\n".join(lines)
