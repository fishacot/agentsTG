"""Individual agent bot implementation."""

import logging
from typing import Optional

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.strategy import FSMStrategy

from src.agents_tg.bot.middlewares import RateLimitMiddleware
from src.agents_tg.bots.handlers import callbacks, commands, inbound
from src.agents_tg.bots.telegram_connection import TELEGRAM_CONNECT_SEMAPHORE
from src.agents_tg.services.agent_identity import AGENT_IDENTITIES, get_agent_identity

logger = logging.getLogger(__name__)


class AgentStates(StatesGroup):
    """FSM states for agent bot."""

    idle = State()
    processing = State()


class AgentBot:
    """Individual Telegram bot for a specific agent."""

    def __init__(
        self,
        agent_key: str,
        bot_token: str,
        username: str,
    ):
        self.agent_key = agent_key
        self.username = username.lower().replace("@", "")
        self.identity = get_agent_identity(agent_key)
        self._polling = False

        self.bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(),
        )
        self.dp = Dispatcher(fsm_strategy=FSMStrategy.USER_IN_CHAT)
        self.router = Router()

        self._register_handlers()
        self._register_error_handler()
        self.dp.include_router(self.router)
        self.dp.message.middleware(RateLimitMiddleware(limit=5, window=60))

        logger.info("AgentBot initialized: %s (@%s)", agent_key, self.username)

    def _register_error_handler(self) -> None:
        from aiogram.types import ErrorEvent

        @self.dp.error()
        async def on_error(event: ErrorEvent):
            logger.error(
                "Telegram handler error in %s: %s",
                self.agent_key,
                event.exception,
                exc_info=event.exception,
            )
            return True

    def _register_handlers(self) -> None:
        commands.register_commands(self.router, self)
        callbacks.register_callbacks(self.router, self)
        inbound.register_inbound(self.router, self)

    def get_colleagues_info(self) -> str:
        colleagues = []
        for key, identity in AGENT_IDENTITIES.items():
            if key != self.agent_key:
                username = identity.get("username", key)
                short_desc = identity.get("short_desc", "Агент")
                colleagues.append(f"  • @{username} — {short_desc}")
        return "\n".join(colleagues) if colleagues else "  (нет коллег)"

    def get_colleagues_full_info(self) -> str:
        lines = ["👥 Мои коллеги-агенты:\n"]
        for key, identity in AGENT_IDENTITIES.items():
            if key != self.agent_key:
                username = identity.get("username", key)
                name = identity.get("name", key)
                desc = identity.get("description", "")
                role = identity.get("role", "")
                lines.append(f"\n🤖 @{username}")
                lines.append(f"   Имя: {name}")
                lines.append(f"   Роль: {role}")
                lines.append(f"   Описание: {desc}")
                lines.append(
                    f"   Когда привлекать: {identity.get('when_to_invoke', '')}"
                )
        lines.append(f"\n💡 В группе упоминайте @{self.username} для обращения ко мне")
        lines.append("💡 Используйте @username коллеги для привлечения их")
        return "\n".join(lines)

    async def start(self) -> None:
        logger.info("Starting bot: %s (@%s)", self.agent_key, self.username)

        async with TELEGRAM_CONNECT_SEMAPHORE:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
            except TelegramNetworkError as exc:
                logger.warning(
                    "Webhook delete failed for %s: %s — continuing to polling",
                    self.agent_key,
                    exc,
                )

        self._polling = True
        try:
            await self.dp.start_polling(self.bot, handle_signals=False)
        finally:
            self._polling = False

    async def stop(self) -> None:
        logger.info("Stopping bot: %s", self.agent_key)
        if self._polling:
            try:
                await self.dp.stop_polling()
            except RuntimeError:
                pass
        await self.bot.session.close()

    async def send_message_to_group(
        self, group_id: int, text: str, reply_to: Optional[int] = None
    ) -> None:
        try:
            await self.bot.send_message(
                chat_id=group_id,
                text=text,
                reply_to_message_id=reply_to,
            )
        except Exception as e:
            logger.error("Failed to send message to group from %s: %s", self.agent_key, e)
