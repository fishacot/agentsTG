"""Multi-bot entry point: runs 7 separate Telegram bots (6 agents + orchestrator).

Each agent has its own bot with unique token, username, and identity.
They communicate in a shared group chat via mentions (@username).
"""

import asyncio
import logging
import signal
import sys
from typing import Any, NoReturn

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

    settings = get_settings()

    # Initialize database
    try:
        _db_engine = create_engine()
        from sqlalchemy import text

        from src.agents_tg.db.init_db import init_db
        from src.agents_tg.services.chat_history import chat_history
        from src.agents_tg.services.memory_service import memory_service
        from src.agents_tg.services.reminder_service import reminder_service
        from src.agents_tg.services.shared_context import shared_context
        from src.agents_tg.services.user_contact_service import user_contact_service
        from src.agents_tg.services.user_tasks_service import user_tasks_service

        async with _db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await init_db(_db_engine)
        chat_history.set_pg_available(True)
        memory_service.set_pg_available(True)
        reminder_service.set_pg_engine(_db_engine)
        shared_context.set_pg_engine(_db_engine)
        user_tasks_service.set_pg_engine(_db_engine)
        user_contact_service.set_pg_engine(_db_engine)

        from src.agents_tg.gateway import register_default_hooks
        from src.agents_tg.gateway.job_store import job_store
        from src.agents_tg.services.confirmation_service import confirmation_service
        from src.agents_tg.services.health_server import set_db_engine
        from src.agents_tg.services.plan_executor import plan_executor
        from src.agents_tg.services.plan_recipe_service import plan_recipe_service

        job_store.set_engine(_db_engine)
        plan_executor.set_engine(_db_engine)
        plan_recipe_service.set_pg_engine(_db_engine)
        confirmation_service.set_pg_engine(_db_engine)
        set_db_engine(_db_engine)
        register_default_hooks()
        recovered = await job_store.recover_stale()
        if recovered:
            logger.info("Task Brain recovered %s stale jobs", recovered)

        from src.agents_tg.plugins.role_tools import register_role_tools

        register_role_tools()
        logger.info("✅ Database connected and tables ensured")
    except Exception as e:
        logger.warning(f"⚠️ Database not available: {e}")
        logger.info("   Running without persistence")
        from src.agents_tg.gateway import register_default_hooks

        register_default_hooks()
        from src.agents_tg.plugins.role_tools import register_role_tools

        register_role_tools()

    manager = get_bot_manager()

    async def _reminder_send(
        chat_id: int, user_id: int, body: str, agent_key: str
    ) -> None:
        bot = manager.get_bot(agent_key) or manager.get_bot("personal_assistant")
        if not bot:
            return
        await bot.bot.send_message(chat_id=chat_id, text=body, parse_mode="HTML")

    async def _wake_send(chat_id: int, user_id: int, body: str, agent_key: str) -> None:
        bot = manager.get_bot(agent_key) or manager.get_bot("personal_assistant")
        if not bot:
            return
        await bot.bot.send_message(chat_id=chat_id, text=body)

    from src.agents_tg.services.agent_wake import agent_wake_service
    from src.agents_tg.services.reminder_service import reminder_service

    process_fns: dict[str, Any] = {}
    for agent_key, bot in manager.bots.items():

        def _make_scheduled_process(b=bot):
            async def _scheduled(message, user_text, is_group, coordinator):
                return await b._process_request(
                    message, user_text, is_group, coordinator
                )

            return _scheduled

        process_fns[agent_key] = _make_scheduled_process()

    if process_fns:
        agent_wake_service.set_process_fns(process_fns)
    else:
        pa_bot = manager.get_bot("personal_assistant")
        if pa_bot:

            async def _pa_scheduled_process(message, user_text, is_group, coordinator):
                return await pa_bot._process_request(
                    message, user_text, is_group, coordinator
                )

            agent_wake_service.set_process_fn(_pa_scheduled_process)

    agent_wake_service.set_send_fn(_wake_send)
    reminder_service.set_send_fn(_reminder_send)
    reminder_service.set_digest_fn(agent_wake_service.run_morning_digest)
    reminder_service.set_cron_deliver_fn(agent_wake_service.run_scheduled_reminder)
    await reminder_service.start()
    await agent_wake_service.start()

    from src.agents_tg.services.health_server import start_health_server

    await start_health_server(port=settings.HEALTH_PORT)

    logger.info(f"📡 Registered bots: {list(manager.bots.keys())}")


async def on_shutdown():
    """Actions on system shutdown."""
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    logger = logging.getLogger(__name__)

    logger.info("🛑 Shutting down...")

    from src.agents_tg.services.agent_wake import agent_wake_service
    from src.agents_tg.services.health_server import stop_health_server
    from src.agents_tg.services.reminder_service import reminder_service

    await agent_wake_service.stop()
    await reminder_service.stop()
    await stop_health_server()

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
    logging.getLogger("agents_tg.events").setLevel(logging.INFO)
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
