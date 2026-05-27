"""Multi-bot manager: coordinates 7 separate Telegram bots (6 agents + orchestrator)."""

import asyncio
import logging
from typing import Dict, List, Optional

from aiogram.exceptions import TelegramNetworkError

from src.agents_tg.bots.agent_bot import AgentBot
from src.agents_tg.config import get_settings
from src.agents_tg.services.agent_identity import AGENT_IDENTITIES

logger = logging.getLogger(__name__)

# Delay between starting each bot (seconds) — avoids Windows socket exhaustion
BOT_START_STAGGER_SECONDS = 3.0


class MultiBotManager:
    """Manages multiple agent bots running simultaneously.

    Each agent has its own Telegram bot with unique token.
    All bots can see each other's messages in a shared group.
    """

    def __init__(self):
        self.bots: Dict[str, AgentBot] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    def register_bot(self, agent_key: str, token: str, username: str) -> AgentBot:
        """Register an agent bot."""
        bot = AgentBot(
            agent_key=agent_key,
            bot_token=token,
            username=username,
        )
        self.bots[agent_key] = bot
        logger.info("Registered bot: %s (@%s)", agent_key, username)
        return bot

    def get_bot(self, agent_key: str) -> Optional[AgentBot]:
        """Get a specific bot by agent key."""
        return self.bots.get(agent_key)

    def get_all_bots(self) -> Dict[str, AgentBot]:
        """Get all registered bots."""
        return self.bots.copy()

    async def _run_bot(
        self,
        agent_key: str,
        bot: AgentBot,
        start_delay: float = 0,
    ) -> None:
        """Run one bot with auto-restart on unexpected stop."""
        if start_delay > 0:
            logger.info(
                "Bot %s waiting %.0fs before connect (staggered startup)",
                agent_key,
                start_delay,
            )
            await asyncio.sleep(start_delay)

        retry_delay = 5.0

        while self._running:
            try:
                await bot.start()
                retry_delay = 5.0
            except asyncio.CancelledError:
                logger.info("Bot task cancelled: %s", agent_key)
                break
            except TelegramNetworkError as exc:
                logger.warning(
                    "Bot %s network error (Telegram unreachable): %s",
                    agent_key,
                    exc,
                )
            except Exception:
                logger.exception("Bot %s crashed", agent_key)
            else:
                if not self._running:
                    break
                logger.warning(
                    "Bot %s stopped polling unexpectedly",
                    agent_key,
                )

            if not self._running:
                break

            logger.info(
                "Restarting bot %s in %.0fs...",
                agent_key,
                retry_delay,
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 60.0)

    async def start_all(self):
        """Start all registered bots and keep the process alive."""
        if not self.bots:
            logger.warning("No bots registered!")
            return

        self._running = True
        self._stop_event.clear()
        logger.info(
            "Starting %s bots (staggered %ss apart)...",
            len(self.bots),
            BOT_START_STAGGER_SECONDS,
        )

        self._tasks = [
            asyncio.create_task(
                self._run_bot(
                    key,
                    bot,
                    start_delay=index * BOT_START_STAGGER_SECONDS,
                ),
                name=f"bot_{key}",
            )
            for index, (key, bot) in enumerate(self.bots.items())
        ]

        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            logger.info("Bot supervisor cancelled")

    async def stop_all(self):
        """Stop all bots gracefully."""
        if not self._running and not self._tasks:
            return

        self._running = False
        self._stop_event.set()
        logger.info("Stopping all bots...")

        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        for bot in self.bots.values():
            await bot.stop()

        self._tasks.clear()
        logger.info("All bots stopped")

    async def broadcast_to_group(
        self, group_id: int, message: str, exclude_agent: Optional[str] = None
    ):
        """Broadcast a message to group from all bots (for awareness).

        This creates inter-bot communication where all agents 'see' the message.
        """
        for agent_key, bot in self.bots.items():
            if agent_key != exclude_agent:
                try:
                    await bot.send_message_to_group(group_id, message)
                except Exception as e:
                    logger.warning(f"Failed to broadcast from {agent_key}: {e}")


# Singleton instance
_bot_manager: Optional[MultiBotManager] = None


def get_bot_manager() -> MultiBotManager:
    """Get or create the global bot manager."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = MultiBotManager()
    return _bot_manager


def create_bot_manager_from_settings() -> MultiBotManager:
    """Create and configure bot manager from environment settings.

    Expects these environment variables:
    - BOT_TOKEN_ORCHESTRATOR
    - BOT_TOKEN_PA (Personal Assistant)
    - BOT_TOKEN_CODER
    - BOT_TOKEN_RESEARCH
    - BOT_TOKEN_SECURITY
    - BOT_TOKEN_BUSINESS
    - BOT_TOKEN_MARKETING
    """
    settings = get_settings()
    manager = get_bot_manager()

    # Map agent keys to their token environment variable names
    token_vars = {
        "orchestrator": getattr(settings, "BOT_TOKEN_ORCHESTRATOR", ""),
        "personal_assistant": getattr(settings, "BOT_TOKEN_PA", ""),
        "coder": getattr(settings, "BOT_TOKEN_CODER", ""),
        "research": getattr(settings, "BOT_TOKEN_RESEARCH", ""),
        "security_ai": getattr(settings, "BOT_TOKEN_SECURITY", ""),
        "business_manager": getattr(settings, "BOT_TOKEN_BUSINESS", ""),
        "marketing": getattr(settings, "BOT_TOKEN_MARKETING", ""),
    }

    # Register each bot that has a token
    for agent_key, token in token_vars.items():
        if token:
            identity = AGENT_IDENTITIES.get(agent_key, {})
            username = identity.get("username", agent_key)
            manager.register_bot(agent_key, token, username)
        else:
            logger.warning(f"No token found for {agent_key} - skipping")

    return manager
