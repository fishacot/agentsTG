"""Python plugin registry with plugin.yaml support."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from src.agents_tg.services.agent_runner import AgentTool

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Load and register agent tools from plugin.yaml manifests."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}
        self._plugins: dict[str, dict[str, Any]] = {}

    def register_tool(self, tool: AgentTool, *, plugin_id: str = "core") -> None:
        self._tools[tool.name] = tool
        self._plugins.setdefault(plugin_id, {"tools": []})["tools"].append(tool.name)

    def get_tool(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def tools_for_agent(self, agent_key: str) -> list[AgentTool]:
        return [
            t
            for name, t in self._tools.items()
            if name in _AGENT_TOOL_MAP.get(agent_key, ())
            or name in _AGENT_TOOL_MAP.get("*", ())
        ]

    def load_plugin_yaml(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            plugin_id = str(data.get("id", path.stem))
            self._plugins[plugin_id] = data
            logger.info("Loaded plugin manifest: %s", plugin_id)
        except Exception as exc:
            logger.warning("Failed to load plugin.yaml %s: %s", path, exc)

    def discover(self, plugins_dir: Path) -> None:
        if not plugins_dir.exists():
            return
        for manifest in plugins_dir.glob("*/plugin.yaml"):
            self.load_plugin_yaml(manifest)

    def register_demo_echo_tool(self) -> None:
        if "plugin_echo" in self._tools:
            return

        async def handler(message: str = "", **_: Any) -> dict[str, Any]:
            return {"ok": True, "echo": message or "pong"}

        self.register_tool(
            AgentTool(
                name="plugin_echo",
                description="Demo plugin echo (OpenClaw plugin MVP).",
                parameters={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
                handler=handler,
            ),
            plugin_id="demo",
        )


_AGENT_TOOL_MAP: dict[str, tuple[str, ...]] = {
    "*": ("remember_about_user",),
    "orchestrator": (
        "delegate_task",
        "track_progress",
        "merge_results",
        "plugin_echo",
    ),
    "coder": ("run_code", "lint_test"),
    "research": ("browser_navigate", "browser_snapshot", "deep_research"),
    "security_ai": ("scan_prompt",),
}


plugin_registry = PluginRegistry()
