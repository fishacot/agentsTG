"""Browser tools — httpx fetch with retry and title extraction."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MAX_BYTES = 50_000
_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)


def _extract_title(html: str) -> str:
    m = _TITLE_RE.search(html or "")
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()[:200]


async def _fetch(url: str, *, timeout: float = 15.0) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True
            ) as client:
                return await client.get(url)
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                logger.debug("browser fetch retry %s: %s", url, exc)
    assert last_exc is not None
    raise last_exc


async def browser_navigate(url: str) -> dict[str, Any]:
    """Fetch URL; return title + preview (Playwright-ready interface)."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "invalid url"}

    try:
        resp = await _fetch(url)
        text = resp.text[:_MAX_BYTES]
        title = _extract_title(text)
        return {
            "ok": True,
            "url": str(resp.url),
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "title": title,
            "text_preview": text[:2000],
        }
    except Exception as exc:
        logger.warning("browser_navigate failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def browser_snapshot(url: str) -> dict[str, Any]:
    """Return page text snapshot."""
    result = await browser_navigate(url)
    if not result.get("ok"):
        return result
    return {
        "ok": True,
        "url": result.get("url"),
        "title": result.get("title", ""),
        "snapshot": result.get("text_preview", "")[:8000],
    }
