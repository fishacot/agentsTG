"""Architecture test: agent_bot must not import L3 agents directly."""

import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "personal_assistant",
    "orchestrator",
    "specialists",
}


def test_agent_bot_no_direct_agent_imports():
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "agents_tg"
        / "bots"
        / "agent_bot.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                mod = node.module.split(".")[-1]
                if mod in FORBIDDEN_IMPORTS:
                    found.add(mod)
    assert not found, f"agent_bot imports forbidden L3 modules: {found}"
