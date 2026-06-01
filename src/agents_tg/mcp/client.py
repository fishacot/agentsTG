"""MCP client stub — bridge to external MCP servers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPClient:
    """Minimal MCP bridge stub for future sidecar integration."""

    def __init__(self) -> None:
        self._servers: dict[str, str] = {}
        self._connected = False

    def register_server(self, name: str, url: str) -> None:
        self._servers[name] = url

    async def connect(self) -> bool:
        self._connected = True
        logger.info("MCP stub connected (%s servers)", len(self._servers))
        return True

    async def call_tool(
        self,
        server: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._connected:
            await self.connect()
        if server not in self._servers:
            return {"ok": False, "error": f"unknown server: {server}"}
        logger.debug("MCP stub call %s/%s", server, tool_name)
        return {
            "ok": True,
            "stub": True,
            "server": server,
            "tool": tool_name,
            "args": args,
        }

    async def list_tools(self, server: str) -> list[str]:
        return []


mcp_client = MCPClient()
