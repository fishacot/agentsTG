"""Envelope-first dispatch: bot must not bypass gateway L3 entry."""

import ast
from pathlib import Path

from src.agents_tg.gateway.envelope import OpenClawEnvelope
from src.agents_tg.gateway.router import GatewayRouter


def test_agent_bot_no_dispatch_agent_process():
    """Inbound path uses dispatch_agent(envelope), not legacy dispatch_agent_process."""
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "src/agents_tg/bots/agent_bot.py",
        "src/agents_tg/bots/handlers/inbound.py",
        "src/agents_tg/services/inbound_turn.py",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert "dispatch_agent_process" not in text, rel


def test_inbound_turn_imports_dispatch_agent():
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "agents_tg"
        / "services"
        / "inbound_turn.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.endswith("agent_dispatch"):
                names.update(a.name for a in node.names)
    assert "dispatch_agent" in names


async def test_router_job_fsm_queued_to_running():
    router = GatewayRouter()
    env = OpenClawEnvelope(
        agent_key="personal_assistant",
        user_id=7,
        chat_id=1,
        message_id=99,
        text="hello",
        is_group=False,
    )
    result = await router.dispatch(env)
    assert result.job_id
    assert result.duplicate is False
    await router.complete_job(result.job_id)
