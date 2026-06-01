"""Gateway security hooks package."""

from src.agents_tg.gateway.hook_registry import HookRegistry, hook_registry
from src.agents_tg.gateway.hooks.injection_guard import (
    after_tool_audit,
    before_prompt_injection_guard,
    before_tool_sandbox_guard,
)

hook_registry.register_before_prompt(before_prompt_injection_guard)
hook_registry.register_before_tool(before_tool_sandbox_guard)
hook_registry.register_after_tool(after_tool_audit)

__all__ = ["HookRegistry", "hook_registry"]
