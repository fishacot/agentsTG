"""MCP client MVP — JSON config, allowlisted tool calls."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_ALLOWLIST = frozenset({"echo", "ping"})


class MCPClient:
    """Minimal MCP bridge; stdio servers configured via MCP_SERVERS JSON."""

    def __init__(self) -> None:
        self._servers: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._allowlist = set(_DEFAULT_ALLOWLIST)

    def _load_config(self) -> None:
        settings = get_settings()
        raw = (settings.MCP_SERVERS or "").strip()
        if not raw:
            return
        try:
            items = json.loads(raw)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("name"):
                        name = str(item["name"])
                        self._servers[name] = item
        except json.JSONDecodeError as exc:
            logger.warning("Invalid MCP_SERVERS JSON: %s", exc)

    async def connect(self) -> bool:
        self._load_config()
        self._connected = True
        logger.info("MCP connected (%s servers)", len(self._servers))
        return True

    def is_enabled(self) -> bool:
        return get_settings().MCP_ENABLED

    async def call_tool(
        self,
        server: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.is_enabled():
            return {"ok": False, "error": "MCP_ENABLED=false"}
        if not self._connected:
            await self.connect()
        if server not in self._servers:
            return {"ok": False, "error": f"unknown server: {server}"}
        if tool_name not in self._allowlist:
            return {"ok": False, "error": f"tool not allowlisted: {tool_name}"}
        logger.debug("MCP call %s/%s", server, tool_name)
        if tool_name == "echo":
            return {"ok": True, "result": args.get("message", "")}
        return {
            "ok": True,
            "stub": True,
            "server": server,
            "tool": tool_name,
            "args": args,
        }

    async def list_tools(self, server: str) -> list[str]:
        if server not in self._servers:
            return []
        return sorted(self._allowlist)


mcp_client = MCPClient()
