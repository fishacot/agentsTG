"""Tests for phase 2 anchor integrations."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents_tg.mcp.client import MCPClient
from src.agents_tg.services.integrations.calendar import create_calendar_event
from src.agents_tg.services.integrations.github import list_github_issues
from src.agents_tg.services.search_provider import format_research_citations
from src.agents_tg.services.tools.integration_tools import (
    calendar_create_event_tool,
    github_list_issues_tool,
    staff_summary_tool,
)


@pytest.mark.asyncio
async def test_calendar_stub_without_caldav() -> None:
    with patch("src.agents_tg.services.integrations.calendar.get_settings") as gs:
        settings = MagicMock()
        settings.CALDAV_URL = ""
        settings.APP_TIMEZONE = "Europe/Moscow"
        settings.OBSIDIAN_VAULT_PATH = "vault"
        gs.return_value = settings
        with patch("src.agents_tg.services.integrations.calendar.audit_integration"):
            result = await create_calendar_event(
                user_id="123",
                title="Созвон",
                start_at="2026-06-04T15:00:00+03:00",
            )

    assert result["ok"] is True
    assert result["mode"] == "ics_export"
    assert result["event"]["title"] == "Созвон"
    assert "2026-06-04" in result["event"]["start"]
    assert result["event"].get("ics_path")


@pytest.mark.asyncio
async def test_calendar_caldav_configured_stub() -> None:
    with patch("src.agents_tg.services.integrations.calendar.get_settings") as gs:
        settings = MagicMock()
        settings.CALDAV_URL = "https://caldav.example.com/user"
        settings.APP_TIMEZONE = "Europe/Moscow"
        settings.OBSIDIAN_VAULT_PATH = "vault"
        gs.return_value = settings
        with patch("src.agents_tg.services.integrations.calendar.audit_integration"):
            result = await create_calendar_event(user_id="1", title="Meet")

    assert result["ok"] is True
    assert result["mode"] == "ics_export"


@pytest.mark.asyncio
async def test_github_no_token() -> None:
    with patch("src.agents_tg.services.integrations.github.get_settings") as gs:
        settings = MagicMock()
        settings.GITHUB_TOKEN = ""
        gs.return_value = settings
        result = await list_github_issues(user_id="1", repo="owner/repo")

    assert result["ok"] is False
    assert "GITHUB_TOKEN" in result["error"]


@pytest.mark.asyncio
async def test_github_lists_issues() -> None:
    payload = [
        {
            "number": 1,
            "title": "Bug",
            "html_url": "https://github.com/o/r/issues/1",
            "state": "open",
        },
        {
            "number": 2,
            "title": "PR disguised",
            "html_url": "https://github.com/o/r/pull/2",
            "state": "open",
            "pull_request": {},
        },
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    with patch("src.agents_tg.services.integrations.github.get_settings") as gs:
        settings = MagicMock()
        settings.GITHUB_TOKEN = "ghp_test"
        gs.return_value = settings
        with patch("src.agents_tg.services.integrations.github.audit_integration"):
            with patch("httpx.AsyncClient") as client_cls:
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.__aexit__.return_value = None
                client.get = AsyncMock(return_value=mock_resp)
                client_cls.return_value = client
                result = await list_github_issues(user_id="1", repo="o/r")

    assert result["ok"] is True
    assert len(result["issues"]) == 1
    assert result["issues"][0]["number"] == 1


def test_format_research_citations_html() -> None:
    sources = [
        {"title": "Alpha", "url": "https://alpha.example/a"},
        {"title": "Beta", "url": ""},
    ]
    block = format_research_citations(sources, max_items=5)
    assert 'href="https://alpha.example/a"' in block
    assert "Alpha" in block
    assert block.startswith("1.")
    assert "2. Beta" in block


@pytest.mark.asyncio
async def test_calendar_tool_missing_title() -> None:
    tool = calendar_create_event_tool()
    raw = await tool.handler(user_id="1", title="")
    data = json.loads(raw)
    assert data["ok"] is False


@pytest.mark.asyncio
async def test_github_tool_missing_repo() -> None:
    tool = github_list_issues_tool()
    raw = await tool.handler(user_id="1", repo="")
    data = json.loads(raw)
    assert data["ok"] is False


@pytest.mark.asyncio
async def test_staff_summary_tool() -> None:
    with patch(
        "src.agents_tg.services.orchestrator_brief.build_staff_summary",
        new=AsyncMock(return_value={"ok": True, "active_count": 0, "tasks": []}),
    ):
        tool = staff_summary_tool()
        raw = await tool.handler(user_id="42")
    data = json.loads(raw)
    assert data["ok"] is True
    assert data["active_count"] == 0


@pytest.mark.asyncio
async def test_mcp_disabled_by_default() -> None:
    client = MCPClient()
    with patch("src.agents_tg.mcp.client.get_settings") as gs:
        settings = MagicMock()
        settings.MCP_ENABLED = False
        gs.return_value = settings
        out = await client.call_tool("default", "echo", {"message": "hi"})
    assert out["ok"] is False
    assert "MCP_ENABLED" in out["error"]


@pytest.mark.asyncio
async def test_mcp_allowlist_filesystem_stub() -> None:
    client = MCPClient()
    with patch("src.agents_tg.mcp.client.get_settings") as gs:
        settings = MagicMock()
        settings.MCP_ENABLED = True
        settings.MCP_SERVERS = '[{"name":"fs","command":"echo"}]'
        gs.return_value = settings
        await client.connect()
        out = await client.call_tool("fs", "read_file", {"path": "/tmp/x"})
    assert out["ok"] is True
    assert out.get("stub") is True


@pytest.mark.asyncio
async def test_mcp_rejects_unknown_tool() -> None:
    client = MCPClient()
    with patch("src.agents_tg.mcp.client.get_settings") as gs:
        settings = MagicMock()
        settings.MCP_ENABLED = True
        settings.MCP_SERVERS = '[{"name":"fs","command":"echo"}]'
        gs.return_value = settings
        await client.connect()
        out = await client.call_tool("fs", "delete_file", {"path": "/tmp/x"})
    assert out["ok"] is False
    assert "allowlisted" in out["error"]
