"""Multi-bot system: 6 agents + 1 orchestrator as separate Telegram bots."""

from src.agents_tg.bots.agent_bot import AgentBot
from src.agents_tg.bots.multi_bot_manager import (
    MultiBotManager,
    create_bot_manager_from_settings,
    get_bot_manager,
)

__all__ = [
    "AgentBot",
    "MultiBotManager",
    "create_bot_manager_from_settings",
    "get_bot_manager",
]
