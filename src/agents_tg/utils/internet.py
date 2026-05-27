"""Internet search and web fetching tools for agents."""

import logging
from typing import Dict, List

import trafilatura
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


async def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo.

    Args:
        query: Search query
        max_results: Maximum number of results to return

    Returns:
        List of results with title, href, and body
    """
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            return results
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return []


async def fetch_web_page(url: str) -> str:
    """
    Fetch and extract main content from a web page.

    Args:
        url: Web page URL

    Returns:
        Extracted markdown content or error message
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(
                downloaded,
                include_links=True,
                include_images=False,
                output_format="markdown",
            )
            return content or "Could not extract content from this page."
        return "Failed to fetch the URL."
    except Exception as e:
        logger.error(f"Web fetch error: {e}")
        return f"Error fetching page: {str(e)}"
