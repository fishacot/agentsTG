"""MCP tools exposed to agents when MCP_ENABLED=true."""

from __future__ import annotations

from src.agents_tg.mcp.client import mcp_client
from src.agents_tg.services.tools.builtin import AgentTool, tool_result


def mcp_echo_tool() -> AgentTool:
    async def handler(message: str = "", server: str = "default", **_: object):
        out = await mcp_client.call_tool(server, "echo", {"message": message})
        return tool_result(ok=bool(out.get("ok")), data=str(out))

    return AgentTool(
        name="mcp_echo",
        description="Echo via MCP bridge (allowlisted).",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "server": {"type": "string"},
            },
        },
        handler=handler,
    )
