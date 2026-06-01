"""Browser tools stub — httpx fetch fallback."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MAX_BYTES = 50_000


async def browser_navigate(url: str) -> dict[str, Any]:
    """Fetch URL content (Playwright stub — httpx fallback)."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "invalid url"}

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            text = resp.text[:_MAX_BYTES]
            return {
                "ok": True,
                "url": str(resp.url),
                "status_code": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "text_preview": text,
            }
    except Exception as exc:
        logger.warning("browser_navigate failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def browser_snapshot(url: str) -> dict[str, Any]:
    """Return page text snapshot (same as navigate for stub)."""
    result = await browser_navigate(url)
    if not result.get("ok"):
        return result
    return {
        "ok": True,
        "url": result.get("url"),
        "snapshot": result.get("text_preview", "")[:8000],
    }
