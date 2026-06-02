"""Browser tools title extraction."""

import pytest

from src.agents_tg.sandbox import browser_tools


@pytest.mark.asyncio
async def test_browser_navigate_extracts_title(monkeypatch):
    class FakeResp:
        url = "https://example.com/"
        status_code = 200
        text = "<html><head><title>Example Domain</title></head><body></body></html>"

        @property
        def headers(self):
            return {"content-type": "text/html"}

    async def fake_fetch(url, *, timeout=15.0):
        return FakeResp()

    monkeypatch.setattr(browser_tools, "_fetch", fake_fetch)
    out = await browser_tools.browser_navigate("https://example.com")
    assert out["ok"] is True
    assert out["title"] == "Example Domain"
