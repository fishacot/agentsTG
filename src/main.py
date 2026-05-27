"""Multi-bot entry point: runs 7 separate Telegram bots (6 agents + orchestrator).

Each agent has its own bot with unique token, username, and identity.
They communicate in a shared group chat via mentions (@username).
"""

import asyncio
import logging
import signal
import sys
from typing import NoReturn

from src.agents_tg.bots import create_bot_manager_from_settings, get_bot_manager
from src.agents_tg.bots.group_coordinator import get_coordinator
from src.agents_tg.config import get_settings
from src.agents_tg.db.session import create_engine

# Global DB engine
_db_engine = None
_shutting_down = False


async def on_startup():
    """Actions on system startup."""
    global _db_engine
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting Multi-Agent Bot System")
    logger.info("   6 Agents + 1 Orchestrator")

    # Initialize database
    try:
        _db_engine = create_engine()
        from sqlalchemy import text

        async with _db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connected")
    except Exception as e:
        logger.warning(f"⚠️ Database not available: {e}")
        logger.info("   Running without persistence")

    # Log registered bots
    manager = get_bot_manager()
    logger.info(f"📡 Registered bots: {list(manager.bots.keys())}")


async def on_shutdown():
    """Actions on system shutdown."""
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    logger = logging.getLogger(__name__)

    logger.info("🛑 Shutting down...")

    # Stop all bots
    manager = get_bot_manager()
    await manager.stop_all()

    # Close DB connections
    if _db_engine:
        await _db_engine.dispose()
        logger.info("✅ Database connections closed")

    logger.info("👋 Goodbye!")


def setup_signal_handlers() -> None:
    """Setup graceful shutdown on signals (Unix only)."""
    if sys.platform == "win32":
        return

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(on_shutdown()))


async def main() -> NoReturn:
    """Main entry: initialize and run all bots."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Validate at least one bot token is set
    if not any(
        [
            settings.BOT_TOKEN_ORCHESTRATOR,
            settings.BOT_TOKEN_PA,
            settings.BOT_TOKEN_CODER,
            settings.BOT_TOKEN_RESEARCH,
            settings.BOT_TOKEN_SECURITY,
            settings.BOT_TOKEN_BUSINESS,
            settings.BOT_TOKEN_MARKETING,
        ]
    ):
        logger.error("❌ No bot tokens found!")
        logger.error("   Set BOT_TOKEN_* variables in .env")
        sys.exit(1)

    # Create and start all bots
    manager = create_bot_manager_from_settings()

    if settings.GROUP_CHAT_ID:
        coordinator = get_coordinator()
        coordinator.register_group(
            settings.GROUP_CHAT_ID,
            list(manager.bots.keys()),
        )
        logger.info("Group chat registered: %s", settings.GROUP_CHAT_ID)

    await on_startup()

    if not manager.bots:
        logger.error("❌ No bots could be registered!")
        logger.error("   Check your BOT_TOKEN_* environment variables")
        sys.exit(1)

    logger.info("🤖 Starting %s bots...", len(manager.bots))
    logger.info("   Bots will listen in both DM and group chats")
    logger.info("   ⚠️  НЕ закрывайте это окно! Ctrl+C = остановка всех ботов")

    setup_signal_handlers()

    try:
        await manager.start_all()
    except asyncio.CancelledError:
        logger.info("Main task cancelled")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        raise
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Остановлено пользователем (Ctrl+C). Боты выключены.")
